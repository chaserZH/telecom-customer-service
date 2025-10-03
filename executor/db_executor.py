
"""
数据库执行器
"""
from typing import Dict, Any, Optional

from database import db_manager
from utils import logger, validate_phone


class DatabaseExecutor:
    """数据库执行器 - 执行Function调用"""
    def __init__(self):
        """初始化执行器"""
        self.db = db_manager
        logger.info("数据库执行器初始化完成")

    def execute_function(self, function_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Function调用

        Args:
            function_name: 函数名
            parameters: 参数字典

        Returns:
            执行结果
        """
        logger.info(f"执行Function: {function_name}, 参数: {parameters}")

        # 路由到对应的执行函数
        executor_map = {
            "query_packages": self.query_packages,
            "query_current_package": self.query_current_package,
            "query_package_detail": self.query_package_detail,
            "change_package": self.change_package,
            "query_usage": self.query_usage,
            "business_consultation": self.business_consultation
        }

        executor = executor_map.get(function_name)
        if not executor:
            return {
                "success": False,
                "error": f"未知的函数: {function_name}"
            }

        try:
            result = executor(**parameters)
            logger.info(f"Function执行成功: {function_name}")
            return result
        except Exception as e:
            logger.error(f"Function执行失败: {function_name}, 错误: {e}")
            return {
                "success": False,
                "error": f"执行出错: {str(e)}"
            }

    def query_packages(self,
                       price_min: Optional[float] = None,
                       price_max: Optional[float] = None,
                       data_min: Optional[int] = None,
                       data_max: Optional[int] = None,
                       target_user: Optional[str] = None,
                       sort_by: str = "price_asc") -> Dict[str, Any]:
        """查询套餐列表"""
        # 构建SQL查询
        sql = """
              SELECT id, name, data_gb, voice_minutes, price, target_user, description
              FROM t_packages
              WHERE status = 1 \
              """
        params = {}

        if price_min is not None:
            sql += " AND price >= :price_min"
            params['price_min'] = price_min

        if price_max is not None:
            sql += " AND price <= :price_max"
            params['price_max'] = price_max

        if data_min is not None:
            sql += " AND data_gb >= :data_min"
            params['data_min'] = data_min

        if data_max is not None:
            sql += " AND data_gb <= :data_max"
            params['data_max'] = data_max

        if target_user:
            sql += " AND (target_user = :target_user OR target_user = '无限制')"
            params['target_user'] = target_user

        # 排序
        sort_mapping = {
            "price_asc": "price ASC",
            "price_desc": "price DESC",
            "data_desc": "data_gb DESC"
        }
        sql += f" ORDER BY {sort_mapping.get(sort_by, 'price ASC')}"

        rows = self.db.execute_query(sql, params)

        # 格式化结果
        packages = []
        for row in rows:
            packages.append({
                "id": row[0],
                "name": row[1],
                "data_gb": row[2],
                "voice_minutes": row[3],
                "price": float(row[4]),
                "target_user": row[5],
                "description": row[6]
            })

        return {
            "success": True,
            "data": packages,
            "count": len(packages)
        }

    def query_current_package(self, phone: str) -> Dict[str, Any]:
        """查询用户当前套餐"""
        if not validate_phone(phone):
            return {
                "success": False,
                "error": "手机号格式不正确"
            }

        sql = """
              SELECT p.name, \
                     p.data_gb, \
                     p.voice_minutes, \
                     p.price, \
                     p.target_user, \
                     p.description,
                     u.monthly_usage_gb, \
                     u.monthly_usage_minutes, \
                     u.balance
              FROM t_user u
                       LEFT JOIN t_packages p ON u.current_package_id = p.id
              WHERE u.phone = :phone \
                AND u.status = 1 \
              """

        rows = self.db.execute_query(sql, {"phone": phone})

        if not rows:
            return {
                "success": False,
                "error": "未找到该用户信息"
            }

        row = rows[0]
        return {
            "success": True,
            "data": {
                "phone": phone,
                "package_name": row[0],
                "data_gb": row[1],
                "voice_minutes": row[2],
                "price": float(row[3]),
                "target_user": row[4],
                "description": row[5],
                "monthly_usage_gb": float(row[6]) if row[6] else 0,
                "monthly_usage_minutes": row[7] or 0,
                "balance": float(row[8]) if row[8] else 0
            }
        }

    def query_package_detail(self, package_name: str) -> Dict[str, Any]:
        """查询套餐详情"""
        sql = """
              SELECT id, name, data_gb, voice_minutes, price, target_user, description
              FROM t_packages
              WHERE name = :package_name \
                AND status = 1 \
              """

        rows = self.db.execute_query(sql, {"package_name": package_name})

        if not rows:
            return {
                "success": False,
                "error": f"未找到套餐: {package_name}"
            }

        row = rows[0]
        return {
            "success": True,
            "data": {
                "id": row[0],
                "name": row[1],
                "data_gb": row[2],
                "voice_minutes": row[3],
                "price": float(row[4]),
                "target_user": row[5],
                "description": row[6]
            }
        }

    def change_package(self, phone: str, new_package_name: str) -> Dict[str, Any]:
        """办理套餐变更"""
        if not validate_phone(phone):
            return {
                "success": False,
                "error": "手机号格式不正确"
            }

        # 查找新套餐ID
        sql_package = "SELECT id FROM t_packages WHERE name = :package_name AND status = 1"
        rows = self.db.execute_query(sql_package, {"package_name": new_package_name})

        if not rows:
            return {
                "success": False,
                "error": f"未找到套餐: {new_package_name}"
            }

        package_id = rows[0][0]

        # 更新用户套餐
        sql_update = """
                     UPDATE t_user
                     SET current_package_id = :package_id
                     WHERE phone = :phone \
                     """

        rowcount = self.db.execute_update(sql_update, {
            "package_id": package_id,
            "phone": phone
        })

        if rowcount == 0:
            # 用户不存在,创建新用户
            sql_insert = """
                         INSERT INTO t_user (phone, current_package_id)
                         VALUES (:phone, :package_id) \
                         """
            self.db.execute_update(sql_insert, {
                "phone": phone,
                "package_id": package_id
            })

        return {
            "success": True,
            "message": f"已成功为您办理【{new_package_name}】,次月生效"
        }

    def query_usage(self, phone: str, query_type: str = "all") -> Dict[str, Any]:
        """查询使用情况"""
        if not validate_phone(phone):
            return {
                "success": False,
                "error": "手机号格式不正确"
            }

        sql = """
              SELECT monthly_usage_gb, monthly_usage_minutes, balance
              FROM t_user
              WHERE phone = :phone \
                AND status = 1 \
              """

        rows = self.db.execute_query(sql, {"phone": phone})

        if not rows:
            return {
                "success": False,
                "error": "未找到该用户信息"
            }

        row = rows[0]
        result = {
            "success": True,
            "phone": phone
        }

        if query_type in ["data", "all"]:
            result["monthly_usage_gb"] = float(row[0]) if row[0] else 0
            result["monthly_usage_minutes"] = row[1] or 0

        if query_type in ["balance", "all"]:
            result["balance"] = float(row[2]) if row[2] else 0

        return result

    def business_consultation(self, question: str, business_type: str = "其他") -> Dict[str, Any]:
        """业务咨询 - 预留RAG接口"""
        logger.info(f"业务咨询(RAG预留): {question}, 类型: {business_type}")

        return {
            "success": True,
            "response": "感谢您的咨询!业务咨询功能正在完善中,您可以:\n"
                        "1. 继续询问套餐相关问题\n"
                        "2. 拨打10086人工客服获取详细帮助\n"
                        "3. 访问官网了解更多信息",
            "note": "此处预留RAG接口,未来将接入知识库检索"
        }