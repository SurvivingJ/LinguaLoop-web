"""
Persona Archetypes and Seed Data Pools

Defines 26 persona archetypes and per-language seed data for the
conversation generation system. Language IDs: 1=Chinese, 2=English, 3=Japanese.
"""


# =============================================================================
# ARCHETYPES
# =============================================================================

ARCHETYPES: dict[str, dict] = {
    # --- Family (6) ---
    'protective_parent': {
        'label': 'Protective Parent',
        'category': 'family',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['family'],
        'description': 'Protective, sometimes overbearing parent',
        'age_range': (35, 55),
    },
    'rebellious_teen': {
        'label': 'Rebellious Teen',
        'category': 'family',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['family', 'friends'],
        'description': 'Independent-minded young person pushing boundaries',
        'age_range': (18, 22),
    },
    'supportive_sibling': {
        'label': 'Supportive Sibling',
        'category': 'family',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['family', 'friends'],
        'description': 'Loyal brother/sister who provides emotional support',
        'age_range': (20, 40),
    },
    'wise_grandparent': {
        'label': 'Wise Grandparent',
        'category': 'family',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['family'],
        'description': 'Experienced elder who shares wisdom and stories',
        'age_range': (60, 80),
    },
    'nagging_relative': {
        'label': 'Nagging Relative',
        'category': 'family',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['family'],
        'description': 'Well-meaning but intrusive relative',
        'age_range': (40, 65),
    },
    'new_parent': {
        'label': 'New Parent',
        'category': 'family',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['family', 'friends'],
        'description': 'First-time parent navigating parenthood',
        'age_range': (25, 38),
    },

    # --- Romantic (6) ---
    'hopeless_romantic': {
        'label': 'Hopeless Romantic',
        'category': 'romantic',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['romantic_partners', 'friends'],
        'description': 'Idealistic about love and relationships',
        'age_range': (20, 35),
    },
    'commitment_phobe': {
        'label': 'Commitment Phobe',
        'category': 'romantic',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['romantic_partners', 'friends'],
        'description': 'Avoids serious commitment, values independence',
        'age_range': (25, 40),
    },
    'long_term_partner': {
        'label': 'Long-Term Partner',
        'category': 'romantic',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['romantic_partners', 'family'],
        'description': 'Settled in a relationship, focused on daily life',
        'age_range': (30, 55),
    },
    'jealous_partner': {
        'label': 'Jealous Partner',
        'category': 'romantic',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['romantic_partners'],
        'description': 'Insecure, prone to suspicion in relationships',
        'age_range': (22, 40),
    },
    'supportive_spouse': {
        'label': 'Supportive Spouse',
        'category': 'romantic',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['romantic_partners', 'family'],
        'description': 'Devoted partner who prioritizes family harmony',
        'age_range': (28, 55),
    },
    'new_dater': {
        'label': 'New Dater',
        'category': 'romantic',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['romantic_partners', 'friends'],
        'description': 'Navigating the early stages of dating',
        'age_range': (20, 35),
    },

    # --- Friendship (4) ---
    'loyal_best_friend': {
        'label': 'Loyal Best Friend',
        'category': 'friendship',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends'],
        'description': 'Always there, fiercely loyal',
        'age_range': (20, 45),
    },
    'party_animal': {
        'label': 'Party Animal',
        'category': 'friendship',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends'],
        'description': 'Social butterfly, loves going out',
        'age_range': (20, 35),
    },
    'wise_counselor': {
        'label': 'Wise Counselor',
        'category': 'friendship',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['friends', 'family'],
        'description': 'Thoughtful friend who gives considered advice',
        'age_range': (30, 55),
    },
    'competitive_friend': {
        'label': 'Competitive Friend',
        'category': 'friendship',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends', 'colleagues'],
        'description': 'Subtly competitive, always comparing',
        'age_range': (22, 40),
    },

    # --- Professional (5) ---
    'ambitious_climber': {
        'label': 'Ambitious Climber',
        'category': 'professional',
        'typical_registers': ['semi-formal', 'formal'],
        'typical_relationship_types': ['colleagues'],
        'description': 'Career-driven, focused on advancement',
        'age_range': (25, 40),
    },
    'burnt_out_worker': {
        'label': 'Burnt-Out Worker',
        'category': 'professional',
        'typical_registers': ['informal', 'semi-formal'],
        'typical_relationship_types': ['colleagues', 'friends'],
        'description': 'Exhausted, disillusioned with work',
        'age_range': (30, 50),
    },
    'inspiring_mentor': {
        'label': 'Inspiring Mentor',
        'category': 'professional',
        'typical_registers': ['semi-formal', 'formal'],
        'typical_relationship_types': ['colleagues'],
        'description': 'Experienced professional who guides others',
        'age_range': (40, 60),
    },
    'strict_boss': {
        'label': 'Strict Boss',
        'category': 'professional',
        'typical_registers': ['formal'],
        'typical_relationship_types': ['colleagues'],
        'description': 'Demanding but fair manager',
        'age_range': (35, 55),
    },
    'new_employee': {
        'label': 'New Employee',
        'category': 'professional',
        'typical_registers': ['semi-formal', 'formal'],
        'typical_relationship_types': ['colleagues'],
        'description': 'Fresh starter, eager but uncertain',
        'age_range': (22, 30),
    },

    # --- Service (3) ---
    'patient_service_worker': {
        'label': 'Patient Service Worker',
        'category': 'service',
        'typical_registers': ['semi-formal', 'formal'],
        'typical_relationship_types': ['service', 'strangers'],
        'description': 'Calm professional dealing with the public',
        'age_range': (22, 45),
    },
    'demanding_customer': {
        'label': 'Demanding Customer',
        'category': 'service',
        'typical_registers': ['semi-formal'],
        'typical_relationship_types': ['service', 'strangers'],
        'description': 'Knows what they want and won\'t settle',
        'age_range': (25, 60),
    },
    'helpful_neighbor': {
        'label': 'Helpful Neighbor',
        'category': 'service',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends', 'strangers'],
        'description': 'Friendly community member',
        'age_range': (30, 65),
    },

    # --- Social (3) ---
    'gossip_enthusiast': {
        'label': 'Gossip Enthusiast',
        'category': 'social',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends', 'colleagues'],
        'description': 'Loves sharing news and rumors',
        'age_range': (25, 55),
    },
    'social_media_addict': {
        'label': 'Social Media Addict',
        'category': 'social',
        'typical_registers': ['informal'],
        'typical_relationship_types': ['friends'],
        'description': 'Always connected, references online culture',
        'age_range': (18, 30),
    },
    'community_organizer': {
        'label': 'Community Organizer',
        'category': 'social',
        'typical_registers': ['semi-formal'],
        'typical_relationship_types': ['friends', 'strangers', 'colleagues'],
        'description': 'Active in community, brings people together',
        'age_range': (30, 60),
    },
}


# =============================================================================
# NAME POOLS
# =============================================================================

NAME_POOLS: dict[int, list[str]] = {
    1: [  # Chinese (120 names)
        '张伟', '王芳', '刘强', '陈静', '赵军', '孙丽', '周磊', '吴娜',
        '杨洋', '黄婷', '朱鑫', '林美玲', '马俊', '何文', '郭晓东', '高丽华',
        '罗勇', '梁思雨', '宋雪', '唐志明', '韩露', '冯建国', '徐慧', '沈明',
        '曹雨萱', '彭刚', '邓秀英', '潘伟', '蒋小红', '姚峰', '许丹', '叶成龙',
        '谢芳芳', '吕浩', '苏婉', '任强', '丁晓云', '魏军', '范明明', '余佳',
        '田甜', '董磊', '袁芳', '卢海', '贺晓燕', '龚志强', '文丽丽', '庄伟',
        '尹小梅', '段鹏飞', '雷静', '侯明远', '孟洁', '薛刚', '秦美华', '江涛',
        '白雪', '钟健', '陆婷婷', '廖勇', '石慧', '方浩然', '崔兰', '汪大伟',
        '康秀芝', '毛志远', '夏雨晴', '邱鑫', '翟丽娟', '温强', '涂小芳', '柳明',
        '金美兰', '樊刚', '管秋月', '程建华', '于慧', '顾海洋', '葛丽', '戴志明',
        '万晓燕', '章磊', '闫美', '甘晓峰', '祝芳', '付建国', '俞洁', '安大壮',
        '齐婷', '伍志豪', '常玲', '倪大鹏', '褚小凤', '严华', '项美丽', '洪志远',
        '邵雅琴', '施海明', '牛翠花', '殷阳', '华丹丹', '应超', '左慧兰', '辛刚',
        '杜娟', '柏建军', '苗秀珍', '谭浩', '凌美玉', '史磊', '熊小丽', '乐志明',
        '舒婷', '武海', '阮芳芳', '雍文杰', '米晓红', '贝伟', '成美英', '路阳',
    ],
    2: [  # English (120 names)
        'James Mitchell', 'Emma Thompson', 'Oliver Barnes', 'Sophie Clarke',
        'Daniel Foster', 'Charlotte Price', 'Ryan Cooper', 'Megan Sullivan',
        'Liam Henderson', 'Amara Osei', 'Noah Patel', 'Isabella Garcia',
        'Ethan Brooks', 'Ava Richardson', 'Lucas Kim', 'Priya Sharma',
        'Jack Williams', 'Chloe Bennett', 'Benjamin Hayes', "Grace O'Brien",
        'Aiden Nakamura', 'Fatima Al-Hassan', 'Samuel Reeves', 'Zara Okonkwo',
        'Connor Murphy', 'Hannah Chen', 'Marcus Jefferson', 'Lily Andersen',
        'Jayden Torres', 'Olivia Stewart', 'Kai Tanaka', 'Nadia Petrova',
        'Tyler Morgan', 'Sophia Nguyen', 'Nathan Edwards', 'Emily Watson',
        'Ravi Desai', 'Courtney Blake', 'Diego Ramirez', 'Aaliyah Washington',
        'Thomas Green', 'Rachel Adams', 'William Scott', 'Jessica Lee',
        'Alexander Wright', 'Mia Robinson', 'Henry Turner', 'Abigail Shaw',
        'Sebastian Hall', 'Eleanor Harris', 'Owen Carter', 'Scarlett Young',
        'Caleb Walker', 'Victoria King', 'Isaac Allen', 'Penelope Davis',
        'Leo Martinez', 'Layla Brown', 'Finn Campbell', 'Stella Ross',
        'Jake Palmer', 'Naomi Jenkins', 'Dylan Reed', 'Isla Cox',
        'Maxwell Ward', 'Ruby Howard', 'Adrian Bell', 'Clara Hunt',
        'Patrick Flynn', 'Sienna Grant', 'George Russell', 'Maya Singh',
        'Dominic Hart', 'Ellie Marshall', 'Trevor Boyd', 'Jasmine Park',
        'Vincent Cole', 'Brooke Dixon', 'Xavier Santos', 'Hazel Burke',
        'Cameron Lane', 'Tessa Rhodes', 'Blake Warren', 'Audrey Grant',
        'Miles Perry', 'Leah Stone', 'Oscar Kim', 'Natasha Wood',
        'Rowan Doyle', 'Iris Quinn', 'Elliot Carr', 'Freya Walsh',
        'Tristan Byrne', 'Phoebe Marsh', 'Callum Craig', 'Imogen Fox',
        'Declan Sharp', 'Amelie Dunn', 'Kieran Page', 'Willow Cross',
        'Brandon Frost', 'Daisy Webb', 'Ashton Pope', 'Cora Field',
        'Stefan Novak', 'Alina Volkov', 'Kwame Mensah', 'Yuki Mori',
        'Tariq Hassan', 'Ingrid Larsson', 'Mateo Silva', 'Anya Kozlov',
        'Jamal Carter', 'Mei-Ling Wu', 'Kofi Adjei', 'Sanna Virtanen',
    ],
    3: [  # Japanese (120 names)
        '佐藤健太', '鈴木美咲', '高橋一郎', '田中由美', '伊藤大輔', '渡辺さくら',
        '山本隆', '中村恵子', '小林翔太', '加藤真理', '吉田和也', '松本美穂',
        '山田圭介', '井上千尋', '木村拓也', '林美奈子', '斎藤誠', '清水友美',
        '山口浩一', '森智子', '池田悠人', '橋本麻衣', '阿部直樹', '石川愛',
        '前田光太郎', '藤田裕子', '小川蓮', '岡田菜々子', '後藤春樹', '長谷川瞳',
        '村上陽介', '近藤あかり', '遠藤翼', '青木彩花', '坂本竜馬', '西村真由美',
        '福田大地', '太田千秋', '三浦颯', '藤井桃子',
        '岩崎拓海', '上田奈緒', '松田悠馬', '横山紗英', '金子涼太', '中島彩乃',
        '原田翔', '小野寺結衣', '藤原航', '竹内美月', '河野大樹', '杉山琴音',
        '安藤健吾', '平野沙織', '丸山陸', '荒木優花', '今井勇太', '高木美帆',
        '大塚光', '片山遥', '宮崎海斗', '菊地理恵', '久保拳', '和田詩織',
        '野村修平', '松尾真央', '千葉亮', '内田美雨', '古川仁', '土屋葵',
        '水野慎太郎', '中西彩華', '永井大地', '秋山凛', '佐々木颯太', '島田美鈴',
        '関口翔太', '堀内瑠花', '服部亮介', '柴田萌', '谷口悠真', '新井奏',
        '大野一真', '武田桜', '神田慧', '浜田千夏', '桜井駿', '白石玲奈',
        '川崎輝', '黒田紬', '本田蒼', '星野結菜', '吉川浩平', '須藤明日香',
        '奥村陽太', '望月優奈', '樋口拓真', '相沢風花', '富田海', '植田日向子',
        '飯田慶', '澤田琉花', '栗原航平', '浅野美結', '渡部拓海', '塚本陽菜',
        '新田恭介', '小松咲良', '五十嵐涼', '松井遥香', '梶山蓮', '日高風子',
        '市川仁', '宇野真由', '峰岸拓', '権田彩葉', '仲村一希', '古賀明花',
    ],
}


# =============================================================================
# OCCUPATION POOLS
# =============================================================================

OCCUPATION_POOLS: dict[int, dict[str, list[str]]] = {
    1: {  # Chinese
        'family': [
            '全职妈妈', '小学教师', '护士', '公务员', '超市经理',
            '会计', '银行职员', '快递员', '厨师', '出租车司机',
        ],
        'romantic': [
            '咖啡店老板', '摄影师', '花店店员', '瑜伽教练', '旅行博主',
            '书店店员', '画家', '音乐老师', '甜品师', '自由撰稿人',
        ],
        'friendship': [
            '健身教练', '调酒师', '导游', '记者', '自媒体博主',
            '宠物店老板', '培训师', '插画师', '电台主播', '潜水教练',
        ],
        'professional': [
            '软件工程师', '市场经理', '律师', '建筑师', '产品经理',
            '财务总监', '医生', '设计师', '编辑', '项目经理',
        ],
        'service': [
            '酒店前台', '餐厅服务员', '物业管理员', '客服代表', '导购员',
            '银行柜员', '药店店员', '家政服务员', '维修工', '外卖骑手',
        ],
        'social': [
            '社区工作者', '活动策划', '婚礼策划师', '居委会干部', '志愿者协调员',
            '舞蹈老师', '广场舞领队', '业主委员会主席', '读书会组织者', '社团负责人',
        ],
    },
    2: {  # English
        'family': [
            'primary school teacher', 'nurse', 'accountant', 'stay-at-home parent',
            'supermarket manager', 'postal worker', 'social worker', 'librarian',
            'plumber', 'receptionist',
        ],
        'romantic': [
            'cafe owner', 'photographer', 'florist', 'yoga instructor',
            'travel blogger', 'bookshop assistant', 'artist', 'music teacher',
            'pastry chef', 'freelance writer',
        ],
        'friendship': [
            'personal trainer', 'bartender', 'tour guide', 'journalist',
            'content creator', 'pet shop owner', 'corporate trainer',
            'illustrator', 'radio presenter', 'surf instructor',
        ],
        'professional': [
            'software engineer', 'marketing manager', 'lawyer', 'architect',
            'product manager', 'finance director', 'doctor', 'graphic designer',
            'editor', 'project manager',
        ],
        'service': [
            'hotel receptionist', 'restaurant server', 'property manager',
            'customer service representative', 'retail assistant', 'bank teller',
            'pharmacy assistant', 'housekeeper', 'maintenance technician',
            'delivery driver',
        ],
        'social': [
            'community worker', 'event planner', 'wedding coordinator',
            'neighbourhood watch chair', 'volunteer coordinator', 'dance instructor',
            'fitness class leader', 'residents\' association chair',
            'book club organiser', 'youth group leader',
        ],
    },
    3: {  # Japanese
        'family': [
            '小学校教師', '看護師', '会計士', '専業主婦', 'スーパー店長',
            '郵便局員', 'ソーシャルワーカー', '図書館司書', '配管工', '受付事務',
        ],
        'romantic': [
            'カフェオーナー', '写真家', '花屋店員', 'ヨガインストラクター',
            '旅行ブロガー', '書店員', '画家', '音楽講師', 'パティシエ',
            'フリーライター',
        ],
        'friendship': [
            'パーソナルトレーナー', 'バーテンダー', 'ツアーガイド', '記者',
            'コンテンツクリエイター', 'ペットショップ店員', '研修講師',
            'イラストレーター', 'ラジオDJ', 'ダイビングインストラクター',
        ],
        'professional': [
            'ソフトウェアエンジニア', 'マーケティングマネージャー', '弁護士',
            '建築士', 'プロダクトマネージャー', '財務部長', '医師',
            'グラフィックデザイナー', '編集者', 'プロジェクトマネージャー',
        ],
        'service': [
            'ホテルフロント', 'レストランスタッフ', 'マンション管理人',
            'カスタマーサポート', '販売員', '銀行窓口', '薬局スタッフ',
            '家事代行', 'メンテナンス技術者', '配達員',
        ],
        'social': [
            '地域活動員', 'イベントプランナー', 'ウェディングプランナー',
            '町内会長', 'ボランティアコーディネーター', 'ダンス講師',
            'フィットネスインストラクター', '管理組合理事長',
            '読書会主催者', '青年団リーダー',
        ],
    },
}


# =============================================================================
# PERSONALITY TRAIT POOLS
# =============================================================================

PERSONALITY_TRAIT_POOLS: dict[int, dict[str, list[str]]] = {
    1: {  # Chinese
        'positive': [
            '善良', '乐观', '热情', '有耐心', '幽默', '体贴', '勤奋', '真诚',
            '大方', '开朗', '细心', '勇敢', '谦虚', '独立', '聪明',
        ],
        'negative': [
            '固执', '急躁', '敏感', '犹豫不决', '爱面子', '唠叨', '多疑', '冲动',
            '挑剔', '小气', '懒散', '自以为是', '嫉妒', '悲观', '暴躁',
        ],
        'neutral': [
            '内向', '外向', '传统', '随性', '理性', '感性', '慢热', '直爽',
            '好奇', '安静', '好胜', '念旧', '粗心', '健谈', '慎重',
        ],
        'speaking_style': [
            '说话直接', '语气温柔', '喜欢用成语', '说话慢条斯理', '爱开玩笑',
            '语速快', '说话委婉', '经常反问', '爱举例子', '口头禅多',
            '语气坚定', '偶尔用方言', '喜欢引经据典', '说话简洁', '爱用网络用语',
        ],
    },
    2: {  # English
        'positive': [
            'kind', 'optimistic', 'enthusiastic', 'patient', 'witty',
            'considerate', 'hardworking', 'sincere', 'generous', 'cheerful',
            'detail-oriented', 'brave', 'humble', 'independent', 'sharp',
        ],
        'negative': [
            'stubborn', 'impatient', 'oversensitive', 'indecisive', 'vain',
            'naggy', 'suspicious', 'impulsive', 'picky', 'stingy',
            'lazy', 'know-it-all', 'jealous', 'pessimistic', 'hot-tempered',
        ],
        'neutral': [
            'introverted', 'extroverted', 'traditional', 'laid-back', 'rational',
            'emotional', 'slow to warm up', 'blunt', 'curious', 'quiet',
            'competitive', 'nostalgic', 'absent-minded', 'talkative', 'cautious',
        ],
        'speaking_style': [
            'speaks directly', 'soft-spoken', 'uses idioms often',
            'speaks slowly and deliberately', 'loves cracking jokes', 'fast talker',
            'diplomatically indirect', 'often asks rhetorical questions',
            'loves giving examples', 'has catchphrases', 'speaks firmly',
            'occasional slang', 'quotes proverbs', 'concise speaker',
            'uses internet slang',
        ],
    },
    3: {  # Japanese
        'positive': [
            '優しい', '楽観的', '熱心', '忍耐強い', 'ユーモアがある',
            '思いやりがある', '勤勉', '誠実', '寛大', '明るい',
            '几帳面', '勇敢', '謙虚', '自立している', '鋭い',
        ],
        'negative': [
            '頑固', 'せっかち', '繊細すぎる', '優柔不断', '見栄っ張り',
            'おせっかい', '疑い深い', '衝動的', '気難しい', 'ケチ',
            '怠け者', '自信過剰', '嫉妬深い', '悲観的', '短気',
        ],
        'neutral': [
            '内向的', '外向的', '伝統的', 'マイペース', '理性的',
            '感情的', '人見知り', 'ストレート', '好奇心旺盛', '物静か',
            '負けず嫌い', '懐かしがり', 'おっちょこちょい', 'おしゃべり', '慎重',
        ],
        'speaking_style': [
            'はっきり言う', '穏やかな口調', 'ことわざをよく使う', 'ゆっくり話す',
            '冗談好き', '早口', '遠回しに言う', 'よく反語を使う',
            '例え話が好き', '口癖がある', '力強い口調', '時々方言が出る',
            '故事成語を引用する', '簡潔に話す', 'ネットスラングを使う',
        ],
    },
}


# =============================================================================
# SYSTEM PROMPT TEMPLATES
# =============================================================================

SYSTEM_PROMPT_TEMPLATES: dict[int, str] = {
    1: '你是{name}，{age}岁的{occupation}。你的性格{traits_str}。{speaking_style}。',
    2: 'You are {name}, a {age}-year-old {occupation}. You are {traits_str}. {speaking_style}.',
    3: 'あなたは{name}、{age}歳の{occupation}です。性格は{traits_str}。{speaking_style}。',
}
