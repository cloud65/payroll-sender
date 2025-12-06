import asyncio
import ssl
from email.message import EmailMessage
from os import getenv
from typing import Annotated, List

import aiosmtplib
from fastapi import Depends

from service.parser import ServiceParser

smtp_host = getenv("RP_EMAIL_HOST")
smtp_port = getenv("RP_EMAIL_PORT", "587")
username = getenv("RP_EMAIL_USERNAME")
password = getenv("RP_EMAIL_PASSWORD")
from_email = getenv("RP_EMAIL_FROM")
sender_name = getenv("RP_EMAIL_NAME", "Отправка расчетных листков")


class Sender:

    def __init__(self, parser):
        self.parser = parser
        self.smtp_host = smtp_host
        self.smtp_port = int(smtp_port)
        self.username = username
        self.password = password
        self.from_email = from_email or username
        self.start_tls = True
        self.name = sender_name

    @classmethod
    async def create(cls, parser: ServiceParser):
        return cls(parser)

    async def _send_email(self, report):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        msg = EmailMessage()
        msg["Subject"] = f"Расчетный листок {report.name}"
        msg["From"] = f"{self.name} <{self.from_email}>"
        msg["To"] = f"{report.name} <{report.email}>"

        # HTML формат
        msg.set_content("Ваш почтовый клиент не поддерживает HTML.", subtype="plain")
        msg.add_alternative(report.html or "<p>Нет содержимого</p>", subtype="html")

        async with aiosmtplib.SMTP(
            hostname=self.smtp_host,
            port=self.smtp_port,
            start_tls=self.start_tls,
            tls_context=context,
        ) as smtp:
            if self.username and self.password:
                await smtp.login(self.username, self.password)

            await smtp.send_message(msg)

    async def send(self, items: List):
        reports = await self.parser.reports(items, html=True)

        # Параллельная отправка писем
        tasks = [self._send_email(report) for report in reports]

        # asyncio.gather позволяет отправлять письма одновременно
        await asyncio.gather(*tasks)
        await self.parser.clear(True)


ServiceSender = Annotated[Sender, Depends(Sender.create)]
