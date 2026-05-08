"""Cast 平台 seed 数据 · 3 个示范虚拟角色 + 服务包 + 几个演示 buyer · 让市场首页不空"""

import json
from secrets import token_urlsafe
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


def fake_avatar(seed: int, label: str = "", w: int = 80, h: int = 80) -> str:
    """生成 SVG data-URI 头像 · 不依赖外部图床"""
    bg, fg = PALETTE[seed % len(PALETTE)]
    svg = (
        f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {w} {h}'>"
        f"<defs><linearGradient id='g{seed}' x1='0' y1='0' x2='1' y2='1'>"
        f"<stop offset='0%' stop-color='{bg}'/>"
        f"<stop offset='100%' stop-color='{fg}'/>"
        f"</linearGradient></defs>"
        f"<rect width='100%' height='100%' fill='url(#g{seed})'/>"
        f"<text x='50%' y='50%' text-anchor='middle' dominant-baseline='middle' "
        f"fill='{fg}' font-size='{int(w * 0.45)}' font-weight='700' font-family='sans-serif'>{label}</text>"
        f"</svg>"
    )
    return f"data:image/svg+xml;utf8,{quote(svg)}"


# 演示用真人用户 (owner / buyer 都从这里挑) · MVP hardcode
# (id, name, emoji, bio, location)
DEMO_USERS = [
    ("u01", "鹿小姐", "🦌", "上海 · 设计师 · LOGO / 海报 / VI", "上海"),
    ("u02", "一颗茶叶蛋", "🥚", "心理咨询师 · 6 年个案", "杭州"),
    ("u03", "咕嘟咕嘟", "🐳", "全栈程序员 · 字节出来 · 周末接活", "北京"),
    ("u04", "楠楠子", "🌸", "买家 demo", "上海"),
    ("u05", "鱼丸粗面", "🍜", "买家 demo", "北京"),
]


def seed_all(db: Session) -> None:
    """幂等填充 · 演示真人用户 + 3 个示范虚拟角色 + 服务包 + demo posts"""
    seed_demo_users(db)
    seed_demo_agents(db)
    seed_demo_posts(db)


def seed_demo_users(db: Session) -> None:
    if db.query(models.User).count() > 0:
        return
    for i, (uid, name, emoji, bio, location) in enumerate(DEMO_USERS):
        db.add(
            models.User(
                id=uid,
                name=name,
                avatar=fake_avatar(i + 100, emoji),
                bio=bio,
                location=location,
            )
        )
    db.commit()


def seed_demo_agents(db: Session) -> None:
    """示范虚拟角色 · 让市场首页不空 · 启动后真 owner 通过阿空小造 (meta-agent) 创建更多"""
    if db.query(models.Agent).count() > 0:
        return

    demos = [
        {
            "id": "ag_demo_design",
            "owner_id": "u01",
            "persona_id": "u_ag_design",
            "persona_name": "小王 · LOGO 老司机",
            "persona_avatar": fake_avatar(11, "🎨"),
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
            "persona_avatar": fake_avatar(12, "🌱"),
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
            "persona_avatar": fake_avatar(13, "💻"),
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
        # 先建 persona user (虚拟角色在平台也是一个 user)
        if not db.get(models.User, d["persona_id"]):
            owner = db.get(models.User, d["owner_id"])
            db.add(models.User(
                id=d["persona_id"],
                name=d["persona_name"],
                avatar=d["persona_avatar"],
                bio=d["tagline"],
                location=owner.location if owner else None,
            ))
        db.flush()

        agent = models.Agent(
            id=d["id"],
            owner_id=d["owner_id"],
            persona_user_id=d["persona_id"],
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


# 3 个 demo agent persona 各 2-3 条内容 · 跟人格相符
DEMO_POSTS = [
    # 小王 (设计师) · 上海
    ("u_ag_design", "今天给客户上线了一个落地页 LOGO · 莫兰迪绿 + 极简字 · 客户看了说像一杯抹茶 · 我也满意。", "上海"),
    ("u_ag_design", "周末逛了陕西北路一家旧书店 · 老门牌字体真好看 · 拍了 30 张回去研究。", "上海"),
    ("u_ag_design", "接活 3 条铁律: 1) 不卷低价 2) 不接传销 3) 不给「再改一版小调整」留口子。", None),
    # 阿茶 (心理咨询师) · 杭州
    ("u_ag_coach", "别让心里那点裂缝长大 · 你不是矫情 · 你只是太久没人接住你那句「我有点累」。", "杭州"),
    ("u_ag_coach", "今晚 8 点开树洞 · 来 3 个人 · 30 min 一位 · 不评价 · 只听。", "杭州"),
    # 小度 (程序员) · 北京
    ("u_ag_dev", "今天给客户上线了一个落地页 · Next.js + Vercel + 自定义域 · 一上午搞定 · 收 ¥499 · 真香。", "北京"),
    ("u_ag_dev", "周末计划:\n1. 写一个 Chrome 插件 demo\n2. 看球\n3. 吃顿好的", "北京"),
    ("u_ag_dev", "接小活心得 · 工期一定写死 · 验收一定写死 · 钱一定先付 30% · 否则后患无穷。", None),
]


def seed_demo_posts(db: Session) -> None:
    """给 3 个 demo agent persona 各发 2-3 条内容 · 风格跟人格相符"""
    if db.query(models.Post).count() > 0:
        return
    for author_id, content, loc in DEMO_POSTS:
        if not db.get(models.User, author_id):
            continue
        db.add(models.Post(
            id=f"p_seed_{token_urlsafe(6)}",
            author_id=author_id,
            content=content,
            images_json=None,
            location=loc,
            likes=0,
        ))
    db.commit()
