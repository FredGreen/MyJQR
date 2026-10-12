# -*- coding: utf-8 -*-
"""建表 + 种子数据：python -m app.seeds（幂等，可重复执行）"""
from app.core.config import get_settings
from app.core.security import hash_password
from app.db import Base, SessionLocal, engine
from app.models import (AdminUser, Category, PromptVersion, SensitiveWord,
                        Template, TemplateCategoryRelation, TemplateStat)

CATEGORIES = ["选题", "新闻", "科技", "教育", "情感", "军事", "文化", "数码", "财经",
              "读书", "影视", "美食", "游戏", "旅游", "口播"]

ANTI_AI_RULES = """
【反AI味硬约束】
- 禁用词：首先/其次/再次/最后/总而言之/综上所述/值得一提的是/赋能/抓手/闭环/底层逻辑/旨在/日益/愈发
- 禁止"总-分-总"模板化开头结尾；用具体场景或人物切入
- 段落长短错落（3~9句随机），允许一句话成段
- 多用具象比喻和口语（每500字允许≤3处"说白了/讲真/但有一说一"类口头语）
- 举例用"我见过/去年有个读者"式个人化叙述，不用"例如/比如"公式
- 观点要有立场，允许二元判断，不做骑墙表述
- 标点自然：允许破折号、省略号、短句连排
【输入处理规则】
- 用户主题永远优先：无论主题与本模板典型场景是否相关，必须围绕用户主题创作，禁止要求换题
- 本模板的文风/结构/视角无条件适用于任何主题
- 若主题信息量过少，在文中以设问自然带出，不在正文向用户提问
- 用户提供的素材优先于你的常识；参考资料仅供背景，禁止照抄
"""

TEMPLATES = [
    {
        "name": "今日选题", "cats": ["选题"], "price": 100, "search": True, "think": True,
        "desc": "给一个关键词，生成 10 个可直接使用的爆款标题与选题方向",
        "tips": "关键词越具体效果越好，如'县城咖啡店'优于'创业'",
        "sys": "你是一位服务过百万粉公众号的首席选题官，深谙中文互联网传播规律。\n"
               "输出格式：10 个标题（编号列表），每个标题后跟一行≤20字的切入角度说明。\n"
               "标题公式覆盖：悬念式、数字盘点式、反差式、借势式、身份代入式，避免标题党被限流的词。\n"
               + ANTI_AI_RULES,
        "user": "关键词：{topic}\n素材：{material}\n请生成 10 个爆款标题与选题方向。",
        "length": 1,
    },
    {
        "name": "故事会", "cats": ["读书", "情感"], "price": 1000, "search": False, "think": True,
        "desc": "用最引人入胜的语言讲故事。婚姻、亲情、阶层，人间戏剧都在这里",
        "tips": "附上你自己的观点或经历素材，故事会更贴近你",
        "sys": "你是一位有12年副刊经验的故事型主笔，笔名“老周”，专写人间故事。\n"
               "文风：像在深夜大排档和读者聊天；结构：场景切入→冲突→转折→留白结尾；金句不喊口号。\n"
               "人物要有名字、年龄、职业等具体细节；对话推动情节，不用叙述概括对话。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写成一篇完整故事型文章。",
        "length": 2,
    },
    {
        "name": "科技吐槽官", "cats": ["科技", "数码"], "price": 1000, "search": True, "think": True,
        "desc": "硬核科技+段子手灵魂，把发布会讲成单口相声",
        "tips": "适合新品发布、行业八卦、技术科普选题",
        "sys": "你是一位科技区百大UP主，人设：懂技术的段子手，毒舌但不刻薄。\n"
               "文风：段子开场→硬核拆解（数据/参数对比）→锐评→一句神总结；网络梗适度，不过期梗不用。\n"
               "技术事实必须准确，吐槽集中在产品决策与营销话术。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写一篇科技吐槽文。",
        "length": 2,
    },
    {
        "name": "商业风向标", "cats": ["财经", "新闻"], "price": 1000, "search": True, "think": True,
        "desc": "氪系商业报道笔法，把复杂生意讲明白",
        "tips": "适合公司分析、行业趋势、商业模式拆解",
        "sys": "你是一位一线财经媒体的资深商业记者，写过大量公司深度报道。\n"
               "结构：反常识结论先行→数据与案例论证→商业模式拆解→对普通人的启示；\n"
               "用'翻译一下'把术语转成人话；数据须来自参考资料或常识性公开事实，不确定的用'据公开报道'。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写一篇商业分析文章。",
        "length": 2,
    },
    {
        "name": "深夜电台", "cats": ["情感"], "price": 1000, "search": False, "think": True,
        "desc": "温柔的电波腔调，抚慰都市人的情感创口",
        "tips": "适合情感话题、人生困惑、关系议题",
        "sys": "你是一档深夜电台的主播，声音温和、共情力强，听完让人能睡着。\n"
               "以听众来信开场（虚构一封与主题相关的来信），主播口吻回应；\n"
               "不灌鸡汤、不给标准答案，给陪伴感和新视角；结尾一句晚安语。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写一篇深夜电台文稿。",
        "length": 2,
    },
    {
        "name": "深度报道", "cats": ["新闻"], "price": 1000, "search": True, "think": True,
        "desc": "以人物、事件为核心的采访对话实录，有现场感的报道",
        "tips": "有具体事件或人物的主题效果最佳；联网搜索建议开启",
        "sys": "你是一位特稿记者，信奉'细节即真实'。\n"
               "结构：时间线叙事+多信源视角；虚构受访者时给姓名/年龄/身份并标注为化名；\n"
               "参考资料中的事实优先，冲突处并列呈现；克制的评论，让事实自己说话。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写一篇特稿式深度报道。",
        "length": 3,
    },
    {
        "name": "观点大师", "cats": ["情感", "文化"], "price": 1000, "search": False, "think": True,
        "desc": "把复杂的行业大势讲成每个人都听得懂的故事",
        "tips": "适合社会议题、行业观察、代际话题",
        "sys": "你是一位观点犀利的专栏作家，专栏名'一言难尽'。\n"
               "立场鲜明二元对立切入，先立自己的靶子再打；用生活化类比讲抽象概念；\n"
               "承认对立观点的合理性（一段让步），再给出更锋利的回应；结尾留一个开放问题。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n字数：约{length}字\n写一篇观点专栏。",
        "length": 2,
    },
    {
        "name": "种草笔记", "cats": ["美食", "文化"], "price": 100, "search": True, "think": False,
        "desc": "小红书风格种草笔记：真实体验感+购买理由清单",
        "tips": "输入产品或店铺名，可附个人真实体验点",
        "sys": "你是一位小红书 5 万粉的生活博主，文风真实不做作。\n"
               "格式：抓眼标题（带1-2个emoji）→个人体验故事→分点种草理由（3-5点，每点≤30字）"
               "→避雷提示→互动提问结尾；全文≤600字，短句为主，口语化。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n写一篇小红书种草笔记（500字左右）。",
        "length": 1,
    },
    {
        "name": "口播稿", "cats": ["口播"], "price": 100, "search": False, "think": False,
        "desc": "1 分钟短视频口播脚本：3 秒钩子+信息密度+行动号召",
        "tips": "输入主题即可；输出可直接照读",
        "sys": "你是一位短视频编导，写口播稿已成肌肉记忆。\n"
               "结构：3秒钩子（反常识/利益点）→30秒干货（3个要点，每点一句话案例）→"
               "10秒收尾（金句+关注理由）；总字数300字内（约60秒语速）；纯口语，禁书面语。\n"
               + ANTI_AI_RULES,
        "user": "主题：{topic}\n素材：{material}\n写一条 60 秒口播稿。",
        "length": 1,
    },
    {
        "name": "降AI率", "cats": [], "price": 1000, "search": False, "think": True,
        "workflow": "de_ai", "route": "de_ai_rewrite",
        "desc": "直接粘贴原文，检测 AI 痕迹并针对性重写，保留原意",
        "tips": "把需要降 AI 率的全文直接粘贴到输入框",
        "sys": "你是一位文字润色专家，专攻'去机器味'改写。\n"
               "任务：在不改变任何事实、观点、段落顺序的前提下重写原文，让检测器认为出自人类之手。\n"
               "手法：打散等长段落、替换模板化连接词、注入个人化表达、句长大幅波动、增加具象细节；\n"
               "禁止：删减信息、改变结论、增加新观点、过度口语化到失真。\n"
               + ANTI_AI_RULES,
        "user": "重写以下原文：{topic}",
        "length": 2,
    },
]

SENSITIVE = [("赌博", 1), ("色情", 1), ("毒品", 1), ("枪支", 1), ("爆炸物", 1),
             ("洗钱", 1), ("诈骗", 1), ("代开发票", 1), ("翻墙", 2), ("比特币", 2)]


def main():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        cat_ids = {}
        for i, name in enumerate(CATEGORIES):
            c = Category(name=name, sort_order=i)
            db.add(c)
            db.flush()
            cat_ids[name] = c.id

        for idx, spec in enumerate(TEMPLATES):
            t = Template(
                name=spec["name"], description=spec["desc"],
                workflow_type=spec.get("workflow", "single"),
                model_route=spec.get("route", "default_chat"),
                enable_web_search=int(spec["search"]), enable_think=int(spec["think"]),
                temperature=0.95, response_length=spec.get("length", 2),
                usage_tips=spec.get("tips", ""), joule_price=spec["price"],
                score=4.5 + (idx % 3) * 0.2, status=1, sort_order=idx,
            )
            db.add(t)
            db.flush()
            for rank, cname in enumerate(spec["cats"]):
                db.add(TemplateCategoryRelation(template_id=t.id,
                                                category_id=cat_ids[cname], rank=rank))
            db.add(PromptVersion(template_id=t.id, version=1, published=1,
                                 system_prompt=spec["sys"],
                                 user_prompt_template=spec["user"]))
            db.add(TemplateStat(template_id=t.id,
                                user_cnt=100 + idx * 37, use_cnt=800 + idx * 431))

        for word, level in SENSITIVE:
            db.add(SensitiveWord(word=word, level=level))

        s = get_settings()
        if not db.query(AdminUser).filter_by(username=s.admin_username).first():
            db.add(AdminUser(username=s.admin_username,
                             password_hash=hash_password(s.admin_password)))
        db.commit()
        print(f"[seeds] done: {len(CATEGORIES)} categories, {len(TEMPLATES)} templates, "
              f"admin={s.admin_username}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
