import html
import re

TG_LIMIT = 4000  # Telegram limiti 4096, ozgina zaxira bilan


def md_to_html(text: str) -> str:
    """Gemini/UI dagi Markdown (**qalin**, *kursiv*, `kod`, > iqtibos, # sarlavha) ni Telegram HTML ga o'giradi.

    Telegram'ning eski "Markdown" rejimi **qalin** ni tushunmaydi va ko'pincha "can't parse entities" beradi.
    """
    text = html.escape(text or "", quote=False)
    lines = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            continue
        s = re.sub(r'^(&gt;\s?)+', '', s)                  # > iqtibos belgisi
        m = re.match(r'^#{1,6}\s+(.*)$', s)                 # # Sarlavha
        if m:
            s = f"**{m.group(1)}**"
        s = re.sub(r'^[*\-]\s+', '• ', s)                   # * ro'yxat
        lines.append(s)
    text = "\n".join(lines)

    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^\n]+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<![*\w])\*(?![\s*])([^*\n]+?)(?<!\s)\*(?![*\w])', r'<i>\1</i>', text)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text or "…"


def strip_tags(text: str) -> str:
    return html.unescape(re.sub(r'<[^>]+>', '', text))


def split_chunks(text: str, limit: int = TG_LIMIT):
    """Qatorlar bo'yicha bo'ladi — teglar bir qator ichida bo'lgani uchun buzilmaydi."""
    chunks, cur = [], ""
    for line in text.split("\n"):
        while len(line) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(line[:limit])
            line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            chunks.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        chunks.append(cur)
    return chunks or ["…"]
