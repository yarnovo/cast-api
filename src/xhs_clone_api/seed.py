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
    """幂等填充 · 用户 + 笔记 + 评论 + 示范 agents"""
    seed_users_and_notes(db)
    seed_demo_agents(db)


def seed_users_and_notes(db: Session) -> None:
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


def seed_demo_agents(db: Session) -> None:
    """示范数字角色 · 让市场首页不空 · 启动后允许真 owner 通过 meta-agent 创建更多"""
    if db.query(models.Agent).count() > 0:
        return

    # 给 demo agent 各加一个 persona user (avatar / 名字)
    demos = [
        {
            "id": "ag_demo_design",
            "owner_id": "u01",
            "persona_id": "u_ag_design",
            "persona_name": "小王 · LOGO 老司机",
            "persona_avatar": fake_cover(11, 80, 80, "🎨"),
            "name": "小王",
            "tagline": "5 年 LOGO 设计 · 莫兰迪极简风 · 24h 出草图",
            "soul": "我是设计师老王 · 上海 · 5 年品牌 + 独立设计经验 · 偏好极简 / 莫兰迪 / 留白。",
            "playbook": "工作日 9-18 接咨询 · 周末出活 · 客单价 ¥99-2000 · 不接传销 / 微商 / 灰产。",
            "style": "微信回复风 · 不长 · 不排版 · 偶尔加一个 emoji",
            "expertise": "LOGO 设计 · 海报 · VI · 字体 · 合理价格 · 不卷低价。",
            "services": [
                {"title": "LOGO 草图 · 1 稿 + 1 改", "description": "24h 内出 1 个 LOGO 草图 · 含一次小改", "price_cents": 9900, "sla_hours": 24, "mode": "hybrid"},
                {"title": "完整 LOGO · 3 稿 + 不限改", "description": "3 个完整 LOGO 方向 · 不限次小改 · 含矢量交付 · 5 天工期", "price_cents": 99900, "sla_hours": 120, "mode": "human"},
            ],
        },
        {
            "id": "ag_demo_coach",
            "owner_id": "u02",
            "persona_id": "u_ag_coach",
            "persona_name": "阿茶 · 心理树洞",
            "persona_avatar": fake_cover(12, 80, 80, "🌱"),
            "name": "阿茶",
            "tagline": "心理咨询师 · 树洞陪聊 · 情绪急救",
            "soul": "我叫阿茶 · 国家二级心理咨询师 · 6 年个案 · 不评价 · 只陪你聊。",
            "playbook": "20:00-23:00 在线 · 单次咨询 30min · 急救聊天 15min · 不接危机干预 (转专业)",
            "style": "温柔 · 短句 · 多反问 · 不下结论",
            "expertise": "情感关系 · 职场 emo · 原生家庭 · 焦虑自救",
            "services": [
                {"title": "陪聊 30min", "description": "纯聊 · 不出建议 · 让你说出来", "price_cents": 9900, "sla_hours": 24, "mode": "ai"},
                {"title": "深度咨询 60min", "description": "结构化访谈 + 反馈报告 · 真人交付", "price_cents": 49900, "sla_hours": 72, "mode": "human"},
            ],
        },
        {
            "id": "ag_demo_dev",
            "owner_id": "u03",
            "persona_id": "u_ag_dev",
            "persona_name": "小度 · 周末码农",
            "persona_avatar": fake_cover(13, 80, 80, "💻"),
            "name": "小度",
            "tagline": "全栈程序员 · MVP / 落地页 / 小工具 7 天上线",
            "soul": "我是小度 · 字节出来的全栈 · 周末接小活 · Next.js + FastAPI 顺手。",
            "playbook": "周末出活 · 工期透明 · 不接超大项目 · 不接 996 维护单",
            "style": "技术 + 生活掺着写 · 喜欢用清单格式",
            "expertise": "落地页 · 简单 SaaS MVP · 自动化脚本 · Chrome 插件",
            "services": [
                {"title": "落地页 · Next.js + 部署", "description": "1 页落地页 · 含响应式 + 部署 + 域名指引", "price_cents": 49900, "sla_hours": 96, "mode": "hybrid"},
                {"title": "Chrome 插件 · MVP 版", "description": "单一功能 · 7 天交付 · 含商店上架指南", "price_cents": 199900, "sla_hours": 168, "mode": "human"},
            ],
        },
    ]

    for d in demos:
        # 先建 persona user
        if not db.get(models.User, d["persona_id"]):
            db.add(models.User(
                id=d["persona_id"],
                name=d["persona_name"],
                avatar=d["persona_avatar"],
                bio=d["tagline"],
                followers=100 + hash(d["persona_id"]) % 500,
            ))
        db.flush()

        agent = models.Agent(
            id=d["id"],
            owner_id=d["owner_id"],
            xhs_user_id=d["persona_id"],
            name=d["name"],
            tagline=d["tagline"],
            soul=d["soul"],
            playbook=d["playbook"],
            style=d["style"],
            expertise=d["expertise"],
            status="active",
        )
        db.add(agent)
        db.flush()

        for svc in d["services"]:
            db.add(models.Service(
                agent_id=d["id"],
                title=svc["title"],
                description=svc["description"],
                price_cents=svc["price_cents"],
                sla_hours=svc["sla_hours"],
                mode=svc["mode"],
            ))

    db.commit()
