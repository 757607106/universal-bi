import pandas as pd
from sqlalchemy import create_engine, text
from faker import Faker
import random
import datetime
from urllib.parse import quote_plus

# --- 配置 ---
DB_HOST = '192.168.13.158'
DB_PORT = 3306
DB_USER = 'root'
DB_PASSWORD = quote_plus('JZP!@#jzp366')
DB_NAME = 'bi_demo_data'

# --- 初始化 Faker ---
fake = Faker(locale='zh_CN')

def create_database_if_not_exists():
    """
    连接到 MySQL 服务器（不指定库），如果库不存在则创建。
    """
    # 连接字符串，不带数据库名
    db_url_no_db = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}"
    engine = create_engine(db_url_no_db)
    
    try:
        with engine.connect() as conn:
            # 自动提交模式，创建数据库
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            print(f"✅ 数据库检查/创建成功: {DB_NAME}")
    except Exception as e:
        print(f"❌ 创建数据库失败: {e}")
        exit(1)
    finally:
        engine.dispose()

def get_db_engine():
    """
    获取连接到目标数据库的 engine
    """
    db_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(db_url)

def generate_dim_products(num=30):
    """
    生成商品维表数据
    """
    categories = ['电子', '服装', '家居', '食品']
    data = []
    
    for i in range(1, num + 1):
        category = random.choice(categories)
        cost = round(random.uniform(10, 500), 2)
        # 售价在成本基础上加价 20% - 100%
        price = round(cost * random.uniform(1.2, 2.0), 2)
        
        # 根据类别生成更有意义的商品名 (简单模拟)
        if category == '电子':
            name = fake.word() + "手机" if random.random() > 0.5 else fake.word() + "耳机"
        elif category == '服装':
            name = fake.word() + "T恤" if random.random() > 0.5 else fake.word() + "牛仔裤"
        elif category == '家居':
            name = fake.word() + "沙发" if random.random() > 0.5 else fake.word() + "台灯"
        else:
            name = fake.word() + "零食"
            
        data.append({
            'product_id': i,
            'product_name': name,
            'category': category,
            'cost': cost,
            'price': price
        })
    
    return pd.DataFrame(data)

def generate_dim_users(num=50):
    """
    生成用户维表数据
    """
    cities = ['北京', '上海', '广州', '深圳', '杭州', '成都']
    genders = ['男', '女']
    data = []
    
    for i in range(1, num + 1):
        data.append({
            'user_id': i,
            'username': fake.user_name(),
            'city': random.choice(cities),
            'gender': random.choice(genders),
            'join_date': fake.date_between(start_date='-2y', end_date='today')
        })
        
    return pd.DataFrame(data)

def generate_fact_orders(users_df, products_df, num=1000):
    """
    生成订单事实表数据
    """
    user_ids = users_df['user_id'].tolist()
    product_ids = products_df['product_id'].tolist()
    # 创建 product_id -> price 的映射，方便计算 total_amount
    price_map = products_df.set_index('product_id')['price'].to_dict()
    
    statuses = ['已支付', '已支付', '已支付', '已支付', '已退款'] # 增加已支付的概率
    data = []
    
    # 时间范围：过去 12 个月
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    for i in range(1, num + 1):
        uid = random.choice(user_ids)
        pid = random.choice(product_ids)
        quantity = random.randint(1, 5)
        price = price_map[pid]
        total_amount = round(price * quantity, 2)
        order_date = fake.date_between(start_date=start_date, end_date=end_date)
        status = random.choice(statuses)
        
        data.append({
            'order_id': i,
            'user_id': uid,
            'product_id': pid,
            'quantity': quantity,
            'total_amount': total_amount,
            'order_date': order_date,
            'status': status
        })
        
    return pd.DataFrame(data)

def main():
    print("🚀 开始生成 BI 测试数据...")
    
    # 1. 确保数据库存在
    create_database_if_not_exists()
    
    engine = get_db_engine()
    
    # 2. 生成数据
    print("📦 生成商品数据 (dim_products)...")
    df_products = generate_dim_products(30)
    
    print("👤 生成用户数据 (dim_users)...")
    df_users = generate_dim_users(50)
    
    print("📝 生成订单数据 (fact_orders)...")
    df_orders = generate_fact_orders(df_users, df_products, 1000)
    
    # 3. 写入数据库
    # 使用 if_exists='replace' 如果表存在则覆盖，方便重复测试
    try:
        print("💾 正在写入数据库...")
        
        # 写入 dim_products
        df_products.to_sql('dim_products', engine, if_exists='replace', index=False)
        with engine.connect() as conn:
            # pandas to_sql 创建的表没有主键，需要手动添加
            conn.execute(text("ALTER TABLE dim_products ADD PRIMARY KEY (product_id)"))
        
        # 写入 dim_users
        df_users.to_sql('dim_users', engine, if_exists='replace', index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE dim_users ADD PRIMARY KEY (user_id)"))
            
        # 写入 fact_orders
        df_orders.to_sql('fact_orders', engine, if_exists='replace', index=False)
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE fact_orders ADD PRIMARY KEY (order_id)"))
            # 添加外键约束 (可选，为了数据完整性推荐)
            # 注意：如果多次运行 replace，外键可能会导致 drop table 失败，这里简单起见不加外键约束，或者先 drop
            # 这里的 replace 策略是 pandas 的，它会 drop table if exists。
            # 如果有外键，drop 可能会失败。为了简单脚本，暂时不加物理外键约束。
        
        print(f"✅ 数据生成完毕，库名: {DB_NAME}")
        print(f"   - dim_products: {len(df_products)} 条")
        print(f"   - dim_users: {len(df_users)} 条")
        print(f"   - fact_orders: {len(df_orders)} 条")
        
    except Exception as e:
        print(f"❌ 写入数据失败: {e}")
        # 如果是因为主键已存在等原因（虽然用了 replace），可以忽略或调试
        # 如果是因为 replace 时 drop table 失败（例如有外键依赖），则需要先手动 drop

if __name__ == "__main__":
    main()
