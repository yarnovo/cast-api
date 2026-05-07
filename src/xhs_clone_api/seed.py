"""跟前端 src/data/mock.ts 1:1 对应的 seed 数据"""

from urllib.parse import quote

from sqlalchemy.orm import Session

from . import models


PALETTE = [
    ("#ffe5ec", "#ff8fa3"),
    ("#fef3c7", "#f59e0b"),
    ("#dbeafe", "#3b82f6"),
    ("#dcfce7", "#22c55e"),
    ("#fce7f3", "#ec4899"),
    ("#ede9fe", "#8b5cf6"),
    ("#fed7aa", "#fb923c"),
    ("#cffafe", "#06b6d4"),
]


def fake_cover(seed: int, w: int = 400, h: int = 600, label: str = "") -> str:
    bg, fg = PALETTE[seed % len(PALETTE)]
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'>"
        f"<defs><linearGradient id='g{seed}' x1='0' y1='0' x2='1' y2='1'>"
        f"<stop offset='0%' stop-color='{bg}'/>"
        f"<stop offset='100%' stop-color='{fg}'/>"
        f"</linearGradient></defs>"
        f"<rect width='100%' height='100%' fill='url(#g{seed})'/>"
        f"<circle cx='{int(w * 0.7)}' cy='{int(h * 0.3)}' r='{int(w * 0.18)}' fill='{fg}' opacity='0.4'/>"
        f"<circle cx='{int(w * 0.25)}' cy='{int(h * 0.7)}' r='{int(w * 0.12)}' fill='{bg}' opacity='0.7'/>"
        f"<text x='50%' y='50%' text-anchor='middle' dominant-baseline='middle' "
        f"fill='{fg}' font-size='{int(w * 0.08)}' font-weight='700' font-family='sans-serif'>{label}</text>"
        f"</svg>"
    )
    return f"data:image/svg+xml;utf8,{quote(svg)}"


TITLES = [
    "上海周末漫步｜外滩到武康路 city walk 路线分享",
    "租房避雷指南 ❌ 看了 50 套房总结的 10 个坑",
    "一个人吃饭也要好好做｜本周 5 天减脂餐打卡",
    "终于！把 30㎡ 出租屋改成了 ins 风",
    "日系穿搭 | 春日通勤 5 套 look 都在这",
    "巴厘岛保姆级攻略｜7 天 6 晚人均 5k",
    "化妆台收纳大改造｜从混乱到整齐只花了 100 块",
    "猫咪绝育手册｜从挂号到拆线全流程",
    "考研上岸｜双非 -> 985 二战经验贴",
    "北京胡同里的私房菜｜小众但绝对值得",
    "宿舍党也能拥有的氛围感卧室",
    "产后修复｜骨盆带 + 瑜伽 90 天瘦回 90 斤",
    "相机推荐 | 5000 元以内入门相机怎么选",
    "深夜 emo 怎么办｜情绪自救 8 个方法",
    "健身 1 年｜从 130 斤到 100 斤的真实记录",
    "日本药妆必买清单｜不踩雷",
    "咖啡入门｜手冲 vs 意式怎么选",
    "装修日记 day 88｜终于贴完瓷砖了",
    "雅思 7.5 分｜口语备考 30 天血泪史",
    "猫粮测评｜进口 vs 国产 谁性价比更高",
]

AUTHORS = [
    ("u01", "鹿小姐", "🦌"),
    ("u02", "一颗茶叶蛋", "🥚"),
    ("u03", "咕嘟咕嘟", "🐳"),
    ("u04", "楠楠子", "🌸"),
    ("u05", "鱼丸粗面", "🍜"),
    ("u06", "软糖小姐", "🍬"),
    ("u07", "菜鸟饲养员", "🐰"),
    ("u08", "不爱喝奶茶", "🧋"),
    ("u09", "今天也想躺平", "🛌"),
    ("u10", "周末搬砖人", "🧱"),
]

RATIOS = [1.0, 1.25, 1.33, 1.5, 1.0, 1.4, 1.2, 1.6, 1.1, 1.5, 1.3, 1.0]

SAMPLE_COMMENTS = [
    ("可爱多", "太美了 求链接！", 128),
    ("十三", "这一篇 mark 起来 周末就去 🌟", 56),
    ("阿白", "看完默默收藏了 谢谢博主分享", 33),
    ("橙子味汽水", "我也想试试 但是好怕翻车 😂", 17),
    ("布丁不吃布丁", "终于有人写这个了 等好久", 9),
]


def seed_all(db: Session) -> None:
    """幂等填充：表空才填"""
    if db.query(models.User).count() > 0:
        return

    # users
    for uid, name, emoji in AUTHORS:
        db.add(
            models.User(
                id=uid,
                name=name,
                avatar=fake_cover(int(uid[1:]) + 100, 80, 80, emoji),
                bio="生活记录爱好者",
                followers=200 + int(uid[1:]) * 17,
                following=12,
            )
        )
    db.flush()

    # notes
    base_tags = ["#日常", "#生活记录", "#vlog", "#好物分享"]
    for i, title in enumerate(TITLES):
        uid, _, emoji = AUTHORS[i % len(AUTHORS)]
        ratio = RATIOS[i % len(RATIOS)]
        nid = f"n{i + 1:03d}"
        cover = fake_cover(i, 400, int(400 * ratio), emoji)
        images = [
            fake_cover(i, 800, int(800 * ratio), emoji),
            fake_cover(i + 30, 800, int(800 * ratio), "✨"),
            fake_cover(i + 60, 800, int(800 * ratio), "📷"),
        ]
        db.add(
            models.Note(
                id=nid,
                author_id=uid,
                title=title,
                content="记录一下今天的心情，第一次尝试这件事真的太有趣啦！\n\n关注我，每天分享小确幸 ✨",
                cover=cover,
                images=images,
                tags=base_tags[: 2 + (i % 3)],
                ratio=ratio,
                likes=50 + i * 137 % 9000,
                collects=10 + i * 53 % 1500,
                comments_count=len(SAMPLE_COMMENTS),
            )
        )
    db.flush()

    # comments (前 5 条挂在每条 note 上)
    for i in range(len(TITLES)):
        nid = f"n{i + 1:03d}"
        for j, (cname, ctext, clikes) in enumerate(SAMPLE_COMMENTS):
            uid = AUTHORS[(i + j) % len(AUTHORS)][0]
            db.add(
                models.Comment(
                    id=f"c-{nid}-{j}",
                    note_id=nid,
                    author_id=uid,
                    content=ctext,
                    likes=clikes,
                )
            )

    db.commit()
