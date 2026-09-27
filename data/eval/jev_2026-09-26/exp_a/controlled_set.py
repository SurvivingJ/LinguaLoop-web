# -*- coding: utf-8 -*-
"""Controlled corruption set: 15 real sentences per language (pulled from
LinguaLoop's live word_assets.prompt1_core table, language_id 1=zh/2=en/3=ja),
each hand-corrupted into exactly one of 5 defect types x 3 subtlety levels.
Author: agent, 2026-09-26. Corruptions are deliberate and documented inline;
"subtlety" is the agent's own judgment call, not an empirical measurement.

defect_type in {particle, word_order, verb_form, semantic_anomaly, wrong_sense}
subtlety in {obvious, moderate, subtle}
"""

CONTROLLED = []

def _add(lang, sense_id, correct, corrupted, defect_type, subtlety, note):
    CONTROLLED.append(dict(
        lang=lang, sense_id=sense_id, correct=correct, corrupted=corrupted,
        defect_type=defect_type, subtlety=subtlety, note=note,
    ))

# ---------------------------------------------------------------- zh (15) ---
_add("zh", 10914, "朋友们没在群里发消息。", "朋友们没在群里发消息了。",
     "particle", "obvious", "没...了 co-occurrence clash (没 negates completion, incompatible with 了)")
_add("zh", 34984, "这件毛衣是羊毛的，摸起来很柔软。", "这个毛衣是羊毛的，摸起来很柔软。",
     "particle", "moderate", "wrong measure word 件->个 for 毛衣")
_add("zh", 13001, "坚硬的地让弟弟摔了一跤。", "坚硬地让弟弟摔了一跤。",
     "particle", "subtle", "的->地 turns adjective+noun 'the hard ground' into an adverbial reading")
_add("zh", 21390, "公司今年赚了很多钱。", "公司赚了今年很多钱。",
     "word_order", "obvious", "今年 wedged inside the verb-object, splits 赚了...钱 ungrammatically")
_add("zh", 11136, "很多人都想有一个这样的机器人。", "很多人有都想一个这样的机器人。",
     "word_order", "moderate", "都 relocated after 有, scrambles adverb-verb order")
_add("zh", 20566, "只要用心，他的好品质你也可学到。", "只要用心，你也他的好品质可学到。",
     "word_order", "subtle", "topic-fronted NP reordered; zh's flexible topicalization makes this borderline")
_add("zh", 21382, "我已经把作业写完了。", "我已经把作业写完着了。",
     "verb_form", "obvious", "着+了 stacked after resultative complement 完 -- ungrammatical aspect sequence")
_add("zh", 21818, "两人的感情发展得很顺利。", "两人的感情发展了很顺利。",
     "verb_form", "moderate", "得->了 wrong complement-marking particle before the manner complement")
_add("zh", 10126, "他将我的秘密告诉了别人。", "他将我的秘密告诉着别人。",
     "verb_form", "subtle", "了->着 swaps completed action for a durative aspect that barely fits 告诉")
_add("zh", 34995, "房间散发着一种奇怪的味道。", "房间喝了一种奇怪的味道。",
     "semantic_anomaly", "obvious", "散发着->喝了: a room cannot drink a smell")
_add("zh", 20566, "你周末可和我一起去逛街吗？", "你周末可和我一起去呼吸吗？",
     "semantic_anomaly", "moderate", "逛街->呼吸: 'go breathing together' is odd but not impossible as a joke")
_add("zh", 11136, "大脑温度高的时候，人想打哈欠。", "大脑温度高的时候，人想打伞。",
     "semantic_anomaly", "subtle", "打哈欠->打伞: same 打+object collocation shape, content is quietly nonsensical")
_add("zh", 11136, "很多人都想有一个这样的机器人。", "很多人都想念有一个这样的机器人。",
     "wrong_sense", "obvious", "想(want)->想念(miss/long for a person) does not take 'having a robot' as object")
_add("zh", 20160, "希望你的学习成绩更上一层楼。", "希望你的学习成绩更上一层天。",
     "wrong_sense", "moderate", "fixed idiom 更上一层楼 broken by swapping 楼->天")
_add("zh", 20160, "我们的友谊一定会更上一层楼。", "我们的友谊一定会更上一层楼层。",
     "wrong_sense", "subtle", "楼->楼层: redundant with 一层, breaks the fixed idiom subtly")

# ---------------------------------------------------------------- en (15) ---
_add("en", 15193, "The organization plans to establish a permanent office in the capital next year.",
     "The organization plans to establish a permanent office on the capital next year.",
     "particle", "obvious", "in->on: wrong preposition for a location inside a city")
_add("en", 19848, "The pharmacist handed the prescription bottles across the pharmacy counter.",
     "The pharmacist handed the prescription bottles beside the pharmacy counter.",
     "particle", "moderate", "across->beside: turns a handing-over motion into a static location")
_add("en", 19829, "The wealthy businessman turned his island retreat into his main domicile.",
     "The wealthy businessman turned his island retreat into a main domicile.",
     "particle", "subtle", "his->a: loses possessive specificity, still fluent-sounding")
_add("en", 14891, "During the school play, the large audience laughed at all the funny jokes.",
     "During the school play, laughed the large audience at all the funny jokes.",
     "word_order", "obvious", "subject-verb inversion with no auxiliary")
_add("en", 19463, "The coach focused on technical skills during practice instead of just running laps.",
     "The coach on technical skills focused during practice instead of just running laps.",
     "word_order", "moderate", "PP fronted before the verb it depends on")
_add("en", 13961, "She often begins studying for her history exam a week in advance.",
     "She begins often studying for her history exam a week in advance.",
     "word_order", "subtle", "frequency adverb misplaced after the verb instead of before it")
_add("en", 14298, "He double-checked his backpack to ensure he had brought all his necessary school books.",
     "He double-checked his backpack to ensure he have brought all his necessary school books.",
     "verb_form", "obvious", "had->have: breaks subject-verb agreement / sequence of tenses")
_add("en", 19851, "The teacher tried to personalize the lesson plan for each student.",
     "The teacher tried to personalizing the lesson plan for each student.",
     "verb_form", "moderate", "to+infinitive replaced with to+gerund, a common learner slip")
_add("en", 19835, "The dancers performed a traditional routine that has been passed down for generations.",
     "The dancers performed a traditional routine that had been passed down for generations.",
     "verb_form", "subtle", "has->had: subtly implies the tradition no longer continues")
_add("en", 14468, "Every gentle sound in the quiet forest made him feel a bit nervous.",
     "Every gentle sound in the quiet forest made him feel a bit purple.",
     "semantic_anomaly", "obvious", "nervous->purple: category violation, a feeling cannot be a color")
_add("en", 19835, "For the science project, they built a bespoke case to protect the delicate model.",
     "For the science project, they built a bespoke case to educate the delicate model.",
     "semantic_anomaly", "moderate", "protect->educate: verb-object mismatch, grammatical but odd")
_add("en", 14891, "An engaged audience makes performers feel much more confident during live shows.",
     "An engaged audience makes performers feel much more transparent during live shows.",
     "semantic_anomaly", "subtle", "confident->transparent: plausible-sounding abstract adjective that doesn't quite fit")
_add("en", 14180, "They played traditional music on acoustic instruments at the village gathering.",
     "They played traditional music on acoustic instruments at the village meeting.",
     "wrong_sense", "obvious", "gathering(social)->meeting(formal/business): wrong register for music-and-community context")
_add("en", 19852, "What is the extent of your prior knowledge of quantum mechanics before enrolling in this advanced seminar?",
     "What is the extent of your previous knowledge of quantum mechanics before enrolling in this advanced seminar?",
     "wrong_sense", "moderate", "prior(general antecedent qualification)->previous(a specific past instance): near-synonym, wrong nuance")
_add("en", 19463, "The repair shop handled the complex technical issues quickly and efficiently.",
     "The repair shop handled the complex technical matters quickly and efficiently.",
     "wrong_sense", "subtle", "issues(mechanical problems)->matters(administrative topics): subtle register/sense mismatch")

# ---------------------------------------------------------------- ja (15) ---
_add("ja", 35005, "公園にたくさんの子供がいる。", "公園をたくさんの子供がいる。",
     "particle", "obvious", "に->を: location-existence いる requires に, を is flatly wrong here")
_add("ja", 36299, "自然を守る活動に参加した。", "自然が守る活動に参加した。",
     "particle", "moderate", "を->が: reverses agency, 'nature protects' instead of 'protect nature'")
_add("ja", 38525, "寒い季節には、温かいスープを飲みます。", "寒い季節にも、温かいスープを飲みます。",
     "particle", "subtle", "は->も: 'in cold season [topically]' -> 'even in cold season', both grammatical, subtle nuance shift")
_add("ja", 36001, "この空間はとても明るい。", "とても空間はこの明るい。",
     "word_order", "obvious", "scrambled constituent order, ungrammatical")
_add("ja", 35865, "二人は長い道を共に歩きました。", "二人は長い道共にを歩きました。",
     "word_order", "moderate", "共に inserted before を, breaking the NP+を boundary")
_add("ja", 35857, "現代の技術は進んでいる。", "技術は現代の進んでいる。",
     "word_order", "subtle", "現代の moved out of its NP, leaving an awkward but skimmable structure")
_add("ja", 36191, "あの絵を見た人は、みんな驚きました。", "あの絵を見る人は、みんな驚きました。",
     "verb_form", "obvious", "見た->見る: past->non-past on the relative clause breaks the temporal sequence")
_add("ja", 35053, "彼女は毎朝、運動をします。", "彼女は毎朝、運動をしました。",
     "verb_form", "moderate", "します->しました: present-habitual->past clashes with the habitual adverb 毎朝")
_add("ja", 35011, "発明にはたくさんの工夫が必要だ。", "発明にはたくさんの工夫が必要だった。",
     "verb_form", "subtle", "だ->だった: general/timeless truth quietly demoted to a past-specific claim")
_add("ja", 35059, "その事はよく知っている。", "その事はよく食べている。",
     "semantic_anomaly", "obvious", "知っている->食べている: an abstract 'matter' (事) cannot be eaten")
_add("ja", 35397, "習慣は少しずつ形成される。", "習慣は少しずつ蒸発される。",
     "semantic_anomaly", "moderate", "形成される->蒸発される: habits do not evaporate, but the passive form almost reads as metaphor")
_add("ja", 35143, "その川は歩いて越えられる。", "その川は歩いて計算できる。",
     "semantic_anomaly", "subtle", "越えられる->計算できる: 'can be calculated on foot' pairs oddly with a river, easy to skim past")
_add("ja", 36393, "二人は静かに対話した。", "二人は静かに対戦した。",
     "wrong_sense", "obvious", "対話(dialogue)->対戦(compete/face off): 'quietly competed' is a register/category mismatch")
_add("ja", 37131, "全体の意見をまとめる。", "全部の意見をまとめる。",
     "wrong_sense", "moderate", "全体(the collective whole)->全部(an itemizable total): close synonyms, different nuance")
_add("ja", 35017, "友達が増えてうれしい。", "友達が増して嬉しい。",
     "wrong_sense", "subtle", "増える(grow in number, intransitive, correct for countable friends)->増す(intensify in degree, literary): near-miss verb confusion")

assert len(CONTROLLED) == 45, len(CONTROLLED)
