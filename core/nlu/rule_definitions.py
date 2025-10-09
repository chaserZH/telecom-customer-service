"""
rule definitions
"""

PRE_NLU_RULES = [
            # ===== 规则组1: 套餐办理类 =====
            {
                "name": "办理具体套餐",
                "pattern": r"(办理|换成|更换|变更|我要办理|帮我办理|给我办理|想办理|要办理).{0,5}(经济套餐|畅游套餐|无限套餐|校园套餐)",
                "intent": "change_package",
                "extract": ["new_package_name", "phone"],
                "priority": 10
            },
            {
                "name": "办理套餐（无具体名）",
                "pattern": r"^(我要|想要|想|帮我|给我).{0,3}(办理|办个|开通|换).{0,3}套餐",
                "intent": "query_packages",
                "extract": [],
                "priority": 9
            },
            {
                "name": "上下文办理",
                "pattern": r"^(办理|办|换|要|就这个|就它)$",
                "intent": "change_package",
                "extract": ["new_package_name", "phone"],
                "context_required": True,  # 需要上下文
                "priority": 8
            },

            # ===== 规则组2: 套餐查询类 =====
            {
                "name": "查询具体套餐详情",
                "pattern": r"(查询|查|看|了解|介绍).{0,3}(经济套餐|畅游套餐|无限套餐|校园套餐)",
                "intent": "query_package_detail",
                "extract": ["package_name"],
                "priority": 10
            },
            {
                "name": "查询当前套餐",
                "pattern": r"(我的|当前|现在|我现在).{0,5}(套餐|什么套餐|是什么套餐|用的什么)",
                "intent": "query_current_package",
                "extract": ["phone"],
                "priority": 9
            },
            {
                "name": "查询套餐列表",
                "pattern": r"(有什么|有哪些|推荐|介绍).{0,3}套餐",
                "intent": "query_packages",
                "extract": ["price_max", "data_min"],
                "priority": 8
            },
            {
                "name": "价格查询",
                "pattern": r"(\d+).{0,3}(元|块).{0,3}(以内|以下|左右).{0,5}套餐",
                "intent": "query_packages",
                "extract": ["price_max"],
                "priority": 9
            },

            # ===== 规则组3: 使用情况查询 =====
            {
                "name": "查询流量",
                "pattern": r"(用了|剩余|还有|还剩).{0,5}(多少|几个|多少个).{0,3}(流量|G|GB)",
                "intent": "query_usage",
                "extract": ["phone"],
                "priority": 9
            },
            {
                "name": "查询余额",
                "pattern": r"(话费|余额|账户|剩余).{0,5}(多少|还有)",
                "intent": "query_usage",
                "extract": ["phone"],
                "priority": 9
            },

            # ===== 规则组4: 业务咨询类 =====
            {
                "name": "咨询办理流程",
                "pattern": r"(怎么|如何|怎样).{0,5}(办理|开通|换|变更)",
                "intent": "business_consultation",
                "extract": ["question"],
                "priority": 10
            },
            {
                "name": "咨询办理条件",
                "pattern": r"(办理|开通).{0,5}(需要|要).{0,5}(什么|哪些|条件|手续|资料)",
                "intent": "business_consultation",
                "extract": ["question"],
                "priority": 10
            },
        ]