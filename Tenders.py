import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.message import EmailMessage

all_keyword = ["割草", "油漆", "驅趕", "移除", "修繕", "粉刷", "維護", "修補"]
AMOUNT_THRE = 1000000

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
}

def date_convert(x):
    """
    將民國日期字串（例如 113/04/08）轉成 pandas.Timestamp
    """
    if pd.isna(x) or x is None:
        return pd.NaT

    x = str(x).strip()
    if not x:
        return pd.NaT

    try:
        parts = [int(i) for i in x.split("/")]
        year = parts[0] + 1911
        month = parts[1]
        day = parts[2]
        return pd.Timestamp(year=year, month=month, day=day)
    except:
        return pd.NaT


def crawler():
    today = pd.Timestamp.today().normalize()
    start_date = today - pd.Timedelta(days=30)

    all_tender_list = []

    for keyword in all_keyword:
        url = (
            "https://web.pcc.gov.tw/prkms/tender/common/basic/readTenderBasic"
            f"?pageSize=10000"
            f"&firstSearch=true"
            f"&searchType=basic"
            f"&isBinding=N"
            f"&isLogIn=N"
            f"&level_1=on"
            f"&orgName="
            f"&orgId="
            f"&tenderName={quote(keyword)}"
            f"&tenderId="
            f"&tenderType=TENDER_DECLARATION"
            f"&tenderWay=TENDER_WAY_ALL_DECLARATION"
            f"&dateType=isDate"
            f"&tenderStartDate={start_date.strftime('%Y')+'%2F'+start_date.strftime('%m')+'%2F'+start_date.strftime('%d')}"
            f"&tenderEndDate={today.strftime('%Y')+'%2F'+today.strftime('%m')+'%2F'+today.strftime('%d')}"
        )

        response = requests.get(url, headers=headers, timeout=100, verify=False)
        response.raise_for_status()
        response.encoding = "utf-8"

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("#tpam tr")

        for row in rows:
            cols = row.find_all("td")
            if len(cols) < 9:
                continue

            office_name = cols[1].get_text(strip=True)
            raw_col3 = cols[2].get_text(separator="", strip=True)
            dissemination_date_raw = cols[6].get_text(strip=True)
            deadline_date_raw = cols[7].get_text(strip=True)
            amount_raw = cols[8].get_text(strip=True)

            # 對應 R 的 CaseID 擷取方式
            hw_pos = raw_col3.find("var hw")
            if hw_pos != -1:
                case_id = raw_col3[:hw_pos].replace(" ", "")
            else:
                case_id = raw_col3.replace(" ", "")

            # 對應 R 的 CaseName 擷取方式
            start_marker = "pageCode2Img"
            end_marker = ";$("
            start_pos = raw_col3.find(start_marker)
            end_pos = raw_col3.find(end_marker)

            case_name = re.search(r'pageCode2Img\("(.+?)"\)', cols[2].select_one("#tpam td:nth-child(3) script").string).group(1)

            dissemination_date = date_convert(dissemination_date_raw)
            deadline_date = date_convert(deadline_date_raw)

            try:
                amount = float(amount_raw.replace(",", "").replace("\r", "").replace("\n", "").replace("\t", ""))
            except:
                amount = None

            all_tender_list.append({
                "OfficeName": office_name,
                "CaseID": case_id,
                "CaseName": case_name,
                "DisseminationDate": dissemination_date,
                "DeadlineDate": deadline_date,
                "Amount": amount,
                "Type": keyword
            })

    all_tender = pd.DataFrame(all_tender_list)

    all_tender_sel = all_tender[
        (all_tender["DeadlineDate"] >= today) &
        (all_tender["Amount"].notna()) &
        (all_tender["Amount"] <= AMOUNT_THRE)
    ].copy()


    all_tender_sel = (
        all_tender_sel
        .groupby(
            ["OfficeName", "CaseID", "CaseName", "DisseminationDate", "DeadlineDate", "Amount"],
            dropna=False,
            as_index=False
        )
        .agg({"Type": "、".join})
    )
    
    return(all_tender_sel)


today=pd.Timestamp.today().normalize()
all_tender_sel=crawler()
all_tender_sel.to_excel('標案_'+today.strftime("%Y-%m-%d")+'.xlsx', index=False, sheet_name='DataSheet')
print('Finished Parsing...')


# send email
sender = "1328robert@gmail.com"
password = "iasw fego ieim reor"
receiver = "nanye1yah@gmail.com"

msg = EmailMessage()
msg["Subject"] = '標案 '+today.strftime("%Y-%m-%d")
msg["From"] = sender
msg["To"] = receiver
msg["Cc"] = '1328robert@gmail.com'

body = "Hello, this is an automated email."
msg.attach(MIMEText(body, "plain"))

with open('標案_'+today.strftime("%Y-%m-%d")+'.xlsx', "rb") as f:
    file_data = f.read()
    file_name = '標案_'+today.strftime("%Y-%m-%d")+'.xlsx'
    
msg.add_attachment(
    file_data,
    maintype="application",
    subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    filename=file_name
)

with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
    smtp.starttls()
    smtp.login(sender, password)
    smtp.send_message(msg)