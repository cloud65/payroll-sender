import asyncio
import re
from datetime import datetime, timedelta, timezone
from os import getenv
from os.path import exists as path_exists
from os.path import join as path_join
from typing import Annotated, Optional
from uuid import UUID, uuid4

import aiofiles
from aiofiles import os as aiofiles_os
from fastapi.params import Cookie, Depends
from pydantic import BaseModel, field_validator

month_map = {
    "ЯНВАРЬ": 1,
    "ФЕВРАЛЬ": 2,
    "МАРТ": 3,
    "АПРЕЛЬ": 4,
    "МАЙ": 5,
    "ИЮНЬ": 6,
    "ИЮЛЬ": 7,
    "АВГУСТ": 8,
    "СЕНТЯБРЬ": 9,
    "ОКТЯБРЬ": 10,
    "НОЯБРЬ": 11,
    "ДЕКАБРЬ": 12,
}


async def delete_folder_files(folder: str):
    filenames = await aiofiles_os.listdir(folder)

    tasks = []
    for filename in filenames:
        full_path = f"{folder}/{filename}"
        # Проверяем, что это файл
        if await aiofiles_os.path.isfile(full_path):
            tasks.append(aiofiles_os.remove(full_path))
    await asyncio.gather(*tasks)


class ReportData(BaseModel):
    name: str
    code: str
    period: datetime
    email: str
    html: Optional[str]
    id: UUID

    @field_validator("period", mode="before")
    def parse_russian_period(cls, v):
        if isinstance(v, datetime):
            return v  # уже datetime, возвращаем как есть

        try:
            month_str, year_str = v.strip().upper().split()
            month = month_map[month_str]
            year = int(year_str)
            return datetime(year, month, 1)  # первый день месяца
        except (ValueError, KeyError):
            try:
                return datetime.fromisoformat(v)
            except (ValueError, TypeError):
                pass
        return datetime.fromtimestamp(0)


class Parser:

    def __init__(self, guid: str = None):
        self.guid = guid
        self.cache_dir = getenv("RP_CACHE_DIR", default="out")
        try:
            self.cache_interval = int(getenv("RP_CACHE_INTERVAL", default="1"))
        except ValueError:
            self.cache_interval = 1

    @classmethod
    def get_employes(cls, text: str):
        employees = {}

        for line in text.split("\n"):
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                parts.append("")
                tn, fio, email = parts[0], parts[1], parts[2]
                employees[tn] = {"fio": fio, "email": email or ""}
        return employees

    @classmethod
    def parse(cls, html: str, emp: str):
        employees = cls.get_employes(emp)
        pattern_period = re.compile(
            r"РАСЧЕТНЫЙ&nbsp;ЛИСТОК&nbsp;ЗА&nbsp;(.+?)<", flags=re.IGNORECASE
        )

        pattern = re.compile(r"<TR\b.*?>.*?</TR>", flags=re.IGNORECASE | re.DOTALL)
        tr_list = []
        for match in pattern.finditer(html):
            tr_info = {
                "start": match.start(),
                "end": match.end(),
                "text": match.group(0),
            }
            period_match = pattern_period.search(tr_info["text"])
            if period_match:
                tr_info["period"] = period_match.group(1).replace("&nbsp;", " ").strip()
            tr_list.append(tr_info)

        pattern = re.compile(
            pattern=r"<TD\b[^>]*>\s*(.*?)\s*\(([-A-Za-zА-Яа-я0-9]+)\)\s*</TD>",
            flags=re.IGNORECASE,
        )

        last = None
        for i, tr in enumerate(tr_list):
            if "period" not in tr:
                continue
            if last is not None:
                tr_list[last]["closed"] = i - 1
            last = i
            match = pattern.search(tr_list[i + 1]["text"])
            if not match:
                continue
            full_name = match.group(1)
            code = match.group(2)
            if code not in employees or full_name != employees[code]["fio"]:
                continue
            tr["email"] = employees[code]["email"]
            tr["code"] = code
            tr["full_name"] = full_name

        tr_list[last]["closed"] = len(tr_list) - 1

        head = html[0 : tr_list[0]["start"]]
        foot = html[tr_list[-1]["end"] :]

        result = []
        for row in filter(lambda x: "code" in x, tr_list):
            start = row["start"]
            end = tr_list[row["closed"]]["end"]
            block_html = html[start:end]
            item = ReportData(
                id=uuid4(),
                name=row["full_name"],
                code=row["code"],
                period=row["period"],
                email=row.get("email", ""),
                html=f"{head}{block_html}{foot}",
            )
            result.append(item)
        return result

    @classmethod
    def get_depends(cls, data: Annotated[Optional[str], Cookie()] = None) -> "Parser":
        return cls(data)

    def set_cookie(self, response):
        max_age = 60 * 60 * self.cache_interval
        response.set_cookie(
            key="data", value=self.guid, max_age=max_age, httponly=True, samesite="Lax"
        )

    async def clear(self, dir=False):
        path = path_join(self.cache_dir, self.guid)
        if await aiofiles_os.path.exists(path):
            await delete_folder_files(path)
            if dir:
                await aiofiles_os.rmdir(path)

    async def clear_cache(self):
        base = self.cache_dir

        if not await aiofiles_os.path.exists(base):
            return

        now = datetime.now(timezone.utc)
        dirs = await aiofiles_os.listdir(base)

        for folder in dirs:
            full_path = path_join(base, folder)
            try:
                stat = await aiofiles_os.stat(full_path)
                mtime = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
            except (ValueError, TypeError):
                continue

            # Проверяем: срок жизни директории истёк?
            if now - mtime > timedelta(hours=self.cache_interval):
                try:
                    await delete_folder_files(full_path)
                    await aiofiles_os.rmdir(full_path)
                except (OSError, FileNotFoundError, NotADirectoryError):
                    pass

    async def clear_cache_task(self):
        while True:
            try:
                await self.clear_cache()
            except (OSError, FileNotFoundError, NotADirectoryError):
                pass

            # запуск раз в час
            await asyncio.sleep(60)

    async def create_session(self, report: bytes, employees: bytes):
        self.guid = str(uuid4())
        await self.clear()

        report_text = report.decode("utf-8", errors="ignore")
        employees_text = employees.decode("utf-8", errors="ignore")
        reports = self.parse(report_text, employees_text)

        path = path_join(self.cache_dir, self.guid)
        await aiofiles_os.makedirs(path, exist_ok=True)

        for rep in reports:
            file_name = path_join(path, f"{rep.id}.json")
            async with aiofiles.open(file_name, "w", encoding="utf-8") as f:
                await f.write(rep.model_dump_json(ensure_ascii=False))

    async def reports(self, items=None, html=False):
        path = path_join(self.cache_dir, self.guid)
        result = []
        if not path_exists(path):
            return result
        filenames = await aiofiles_os.listdir(path)
        for file_name in filenames:
            if not file_name.endswith(".json"):
                continue
            if items is not None and UUID(file_name.split(".")[0]) not in items:
                continue
            full_path = path_join(path, file_name)
            async with aiofiles.open(full_path, "r", encoding="utf-8") as f:
                content = await f.read()
                rep = ReportData.model_validate_json(content)
                if not html:
                    rep.html = None
                result.append(rep)
        return sorted(result, key=lambda x: (x.name, x.period))

    async def get_report(self, guid: UUID):
        path = path_join(self.cache_dir, self.guid)
        file_name = path_join(path, f"{guid}.json")
        if not await aiofiles_os.path.exists(file_name):
            return None
        async with aiofiles.open(file_name, "r", encoding="utf-8") as f:
            content = await f.read()
            rep = ReportData.model_validate_json(content)
            return rep.html


ServiceParser = Annotated[Parser, Depends(Parser.get_depends)]
