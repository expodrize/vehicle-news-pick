import os
import smtplib
import requests
import anthropic
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GMAIL_USER = os.environ["GMAIL_USER"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL = os.environ.get("RECIPIENT_EMAIL", GMAIL_USER)


def fetch_vehicle_news() -> list[dict]:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": (
            "electric vehicle OR EV OR autonomous driving OR self-driving car "
            "OR Tesla OR Toyota OR Waymo OR mobility OR automotive OR car industry"
        ),
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 30,
        "apiKey": NEWSAPI_KEY,
    }
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    articles = resp.json().get("articles", [])
    return [
        {
            "title": a["title"],
            "description": a.get("description") or "",
            "source": a["source"]["name"],
            "url": a["url"],
            "publishedAt": a["publishedAt"],
        }
        for a in articles
        if a.get("title") and "[Removed]" not in a.get("title", "")
    ][:25]


def rank_and_summarize(articles: list[dict]) -> str:
    articles_text = "\n\n".join(
        f"{i+1}. [{a['source']}] {a['title']}\n   {a['description']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""あなたは自動車・モビリティ業界に詳しいビジネスアナリストです。
以下の英語ニュース記事リストから、ビジネスパーソン（経営者・マネージャー・投資家）が
今日知っておくべき重要度順にTOP5を選び、日本語で解説してください。

選定基準：
- 業界全体への影響度（EV・自動運転・モビリティのトレンド・市場変化）
- ビジネスへの実用的インパクト
- 新規性・速報性

--- ニュース記事リスト ---
{articles_text}

--- 出力形式（HTML） ---
以下のHTML形式で出力してください（外側のタグは不要、<div>から始めてください）：

<div style="font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 680px; margin: 0 auto; padding: 20px; color: #1a1a1a;">

<div style="background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460); padding: 32px 24px; border-radius: 12px; margin-bottom: 28px; text-align: center;">
  <h1 style="color: #ffffff; font-size: 22px; margin: 0 0 8px 0; letter-spacing: 1px;">🚗 Vehicle Daily Brief</h1>
  <p style="color: #a0aec0; font-size: 13px; margin: 0;">ビジネスパーソンのための自動車・モビリティ最新情報 — {datetime.now(timezone(timedelta(hours=9))).strftime('%Y年%m月%d日')}</p>
</div>

[各ニュースをこの形式で5件：]
<div style="border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; margin-bottom: 16px; background: #ffffff; border-left: 4px solid #0f3460;">
  <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
    <span style="background: #0f3460; color: white; font-size: 12px; font-weight: bold; padding: 3px 10px; border-radius: 20px;">1位</span>
    <span style="color: #718096; font-size: 12px;">[出典名]</span>
  </div>
  <h2 style="font-size: 16px; font-weight: bold; margin: 0 0 10px 0; line-height: 1.5; color: #1a202c;">[日本語タイトル]</h2>
  <p style="font-size: 14px; line-height: 1.8; color: #4a5568; margin: 0 0 12px 0;">[ビジネスパーソン向け解説：なぜ重要か、何が変わるか、何をすべきか、を3〜4文で]</p>
  <a href="[元記事URL]" style="font-size: 12px; color: #0f3460; text-decoration: none;">→ 原文を読む</a>
</div>

[フッター：]
<div style="text-align: center; padding: 20px; color: #a0aec0; font-size: 12px; border-top: 1px solid #e2e8f0; margin-top: 24px;">
  <p style="margin: 0;">Powered by Claude AI · NewsAPI</p>
  <p style="margin: 4px 0 0 0;">毎朝6:30に自動配信</p>
</div>

</div>
"""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def send_email(html_body: str) -> None:
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).strftime("%Y年%m月%d日")
    subject = f"🚗 Vehicle Daily Brief — {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = RECIPIENT_EMAIL

    plain = "HTML形式のメールをご覧ください。"
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
    print(f"✅ メール送信完了 → {RECIPIENT_EMAIL}")


def main():
    print("📡 ニュース取得中...")
    articles = fetch_vehicle_news()
    print(f"   {len(articles)}件取得")

    print("🤖 Claude でランキング・要約生成中...")
    html_content = rank_and_summarize(articles)

    print("📧 メール送信中...")
    send_email(html_content)


if __name__ == "__main__":
    main()
