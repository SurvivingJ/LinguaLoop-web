# ZH Silver Adjudication — Disagreements

## zh_silver_11

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中被小心地取出，并被迅速地运送出需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- Draft errors: [{"span_repro": [22, 36], "span_ref": [22, 36], "subtype": "directional_complement", "subtype_v5_target": "directional_complement", "severity_v2": "critical", "learner_form": "运送出需要进行移植手术的医院", "corrected_form": "运送到需要进行移植手术的医院"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "运送出需要进行移植手术的医院", "corrected_form": "运送到需要进行移植手术的医院", "subtype": "directional_complement", "severity": "major"}]

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 到->出 reverses the direction/target of transport, logically confusing

- Why dropped: severity mismatch on '运送出需要进行移植手术的医院': draft=critical reviewer=major



## zh_silver_12

- REF: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，捐献过程就会立即开始。

- REP: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的捐献者。一旦找到匹配的受者，捐献过程就会立即开始。

- Draft errors: [{"span_repro": [66, 81], "span_ref": [66, 80], "subtype": "word_choice", "subtype_v5_target": "word_choice", "severity_v2": "critical", "learner_form": "在等待名单中寻找最合适的捐献者", "corrected_form": "在等待名单中寻找最合适的受者"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "寻找最合适的捐献者", "corrected_form": "寻找最合适的受者", "subtype": "word_choice", "severity": "major"}]

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 受者->捐献者 swaps recipient/donor roles, factually wrong but locally recoverable from context

- Why dropped: severity mismatch on '在等待名单中寻找最合适的捐献者': draft=critical reviewer=major



## zh_silver_13

- REF: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- REP: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在瞪着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- Draft errors: [{"span_repro": [54, 61], "span_ref": [54, 61], "subtype": "collocation", "subtype_v5_target": "collocation", "severity_v2": "minor", "learner_form": "它好像在瞪着我", "corrected_form": "它好像在看着我"}]

- Draft bands: naturalness=3 range=4

- Reviewer errors: [{"learner_form": "好像在瞪着我", "corrected_form": "好像在看着我", "subtype": "word_choice", "severity": "critical"}]

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 看着->瞪着 inverts the friendly tone established for the smiling cat

- Why dropped: subtype mismatch: draft=collocation reviewer=word_choice (dims naturalness vs fidelity)



## zh_silver_14

- REF: 它提醒我，生活中有很多简单而美好的事物值得我们去发现和珍惜。每次看到它，我都会想起那些无忧无虑的日子，想起那些真心对我好的人。所以，尽管它只是一件普通的T恤，但对我来说，它有着非凡的意义。它是我的“最喜欢的”衣服，因为它代表着舒适、快乐和珍贵的回忆。

- REP: 它提醒我，生活中有很多简单而美好的事物值得我们去发现和珍惜。每次看到它，我都会想起那些无忧无虑的日子，想起那些真心对我好处的人。所以，尽管它只是一件普通的T恤，但对我来说，它有着非凡的意义。它是我的“最喜欢的”衣服，因为它代表着舒适、快乐和珍贵的回忆。

- Draft errors: [{"span_repro": [51, 63], "span_ref": [51, 62], "subtype": "collocation", "subtype_v5_target": "collocation", "severity_v2": "minor", "learner_form": "想起那些真心对我好处的人", "corrected_form": "想起那些真心对我好的人"}]

- Draft bands: naturalness=2 range=4

- Reviewer errors: [{"learner_form": "真心对我好处的人", "corrected_form": "真心对我好的人", "subtype": "orthography", "severity": "minor"}]

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 好->好处 stray extra character breaks grammaticality but intended word is clear

- Why dropped: subtype mismatch: draft=collocation reviewer=orthography (dims naturalness vs accuracy)



## zh_silver_16

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中被小心地取出，被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- Draft errors: [{"span_repro": [17, 24], "span_ref": [17, 25], "subtype": "cohesion_connective", "subtype_v5_target": "cohesion_connective", "severity_v2": "minor", "learner_form": "被迅速地运送到", "corrected_form": "并被迅速地运送到"}]

- Draft bands: naturalness=2 range=4

- Reviewer errors: [{"learner_form": "被小心地取出，被迅速地运送到", "corrected_form": "被小心地取出，并被迅速地运送到", "subtype": "cohesion_connective", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 并 (connective) dropped between clauses

- Why dropped: naturalness mismatch: draft=2 reviewer=3



## zh_silver_17

- REF: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却栩栩如生，充满了生命力。我每次看到这个图案，都会觉得心情变好。我喜欢这件T恤，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。我记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- REP: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却很好看。我每次看到这个图案，都会觉得心情变好。我喜欢这件T恤，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。我记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- Draft errors: [{"span_repro": [23, 28], "span_ref": [23, 36], "subtype": "word_choice", "subtype_v5_target": "word_choice", "severity_v2": "minor", "learner_form": "但却很好看", "corrected_form": "但却栩栩如生，充满了生命力"}]

- Draft bands: naturalness=4 range=3

- Reviewer errors: [{"learner_form": "但却很好看", "corrected_form": "但却栩栩如生，充满了生命力", "subtype": "word_choice", "severity": "major"}]

- Reviewer bands: naturalness=4 range=2

- Reviewer comment: vivid idiom 栩栩如生充满了生命力 flattened to generic 很好看; major fidelity loss and clear range flattening

- Why dropped: severity mismatch on '但却很好看': draft=minor reviewer=major



## zh_silver_18

- REF: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，捐献过程就会立即开始。

- REP: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会看情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，捐献过程就会立即开始。

- Draft errors: [{"span_repro": [46, 50], "span_ref": [46, 65], "subtype": "word_choice", "subtype_v5_target": "word_choice", "severity_v2": "minor", "learner_form": "会看情况", "corrected_form": "会根据患者的身体状况、血型以及配型情况"}]

- Draft bands: naturalness=4 range=2

- Reviewer errors: [{"learner_form": "医疗系统会看情况，在等待名单中寻找", "corrected_form": "医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找", "subtype": "omission", "severity": "critical"}]

- Reviewer bands: naturalness=3 range=2

- Reviewer comment: drops all three matching criteria (身体状况/血型/配型) replaced by vague 看情况; severe content loss and register drop (casual filler in formal medical text) plus range flattening

- Why dropped: severity mismatch on '会看情况': draft=minor reviewer=critical



## zh_silver_19

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工做，并防止身体排斥它。

- Draft errors: [{"span_repro": [5, 15], "span_ref": [5, 16], "subtype": "bei_passive", "subtype_v5_target": "bei_passive", "severity_v2": "major", "learner_form": "会在手术中小心地取出", "corrected_form": "会在手术中被小心地取出"}, {"span_repro": [132, 136], "span_ref": [133, 137], "subtype": "orthography", "subtype_v5_target": "orthography", "severity_v2": "minor", "learner_form": "正常工做", "corrected_form": "正常工作"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "会在手术中小心地取出", "corrected_form": "会在手术中被小心地取出", "subtype": "bei_passive", "severity": "major"}, {"learner_form": "正常工做", "corrected_form": "正常工作", "subtype": "orthography", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 被 (passive marker) dropped; separate typo 工做/工作

- Why dropped: naturalness mismatch: draft=4 reviewer=3



## zh_silver_20

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中被小心的取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- Draft errors: [{"span_repro": [10, 16], "span_ref": [10, 16], "subtype": "de_particles", "subtype_v5_target": "de_particles", "severity_v2": "minor", "learner_form": "被小心的取出", "corrected_form": "被小心地取出"}, {"span_repro": [73, 82], "span_ref": [73, 83], "subtype": "ba_construction", "subtype_v5_target": "ba_construction", "severity_v2": "major", "learner_form": "捐献的健康器官移植", "corrected_form": "将捐献的健康器官移植"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "被小心的取出", "corrected_form": "被小心地取出", "subtype": "de_particles", "severity": "minor"}, {"learner_form": "医生会捐献的健康器官移植到", "corrected_form": "医生会将捐献的健康器官移植到", "subtype": "ba_construction", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 地/的 confusion; 将 (disposal marker) dropped making the clause ungrammatical

- Why dropped: naturalness mismatch: draft=4 reviewer=3



## zh_silver_21

- REF: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却栩栩如生，充满了生命力。我每次看到这个图案，都会觉得心情变好。我喜欢这件T恤，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。我记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- REP: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却栩栩如生，充满了生命力。我每次看到这个图案，都会觉得心情变好。这件T恤我喜欢，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。本人记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- Draft errors: [{"span_repro": [56, 63], "span_ref": [56, 63], "subtype": "topic_comment", "subtype_v5_target": "topic_comment", "severity_v2": "major", "learner_form": "这件T恤我喜欢", "corrected_form": "我喜欢这件T恤"}, {"span_repro": [94, 106], "span_ref": [94, 105], "subtype": "register", "subtype_v5_target": "register", "severity_v2": "major", "learner_form": "本人记得第一次穿这件T恤", "corrected_form": "我记得第一次穿这件T恤"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "这件T恤我喜欢，不仅仅是因为", "corrected_form": "我喜欢这件T恤，不仅仅是因为", "subtype": "word_order", "severity": "minor"}, {"learner_form": "本人记得第一次穿", "corrected_form": "我记得第一次穿", "subtype": "register", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: object-fronting reads slightly stilted before 不仅仅是因为; 本人 is a jarring bureaucratic register clash in a casual reminiscence

- Why dropped: subtype mismatch: draft=topic_comment reviewer=word_order (dims naturalness vs accuracy)



## zh_silver_22

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换功能衰竭的器官。受者移植手术后需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- Draft errors: [{"span_repro": [89, 98], "span_ref": [89, 99], "subtype": "resultative_complement", "subtype_v5_target": "resultative_complement", "severity_v2": "minor", "learner_form": "替换功能衰竭的器官", "corrected_form": "替换掉功能衰竭的器官"}, {"span_repro": [99, 122], "span_ref": [100, 124], "subtype": "word_order", "subtype_v5_target": "word_order", "severity_v2": "major", "learner_form": "受者移植手术后需要接受长期的医疗护理和药物治疗", "corrected_form": "移植手术后，受者需要接受长期的医疗护理和药物治疗"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "替换功能衰竭的器官", "corrected_form": "替换掉功能衰竭的器官", "subtype": "resultative_complement", "severity": "minor"}, {"learner_form": "受者移植手术后需要接受", "corrected_form": "移植手术后，受者需要接受", "subtype": "adverbial_order", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 掉 (resultative complement) dropped; temporal clause 移植手术后 repositioned mid-sentence

- Why dropped: severity mismatch on '受者移植手术后需要接受长期的医疗护理和药物治疗': draft=major reviewer=minor



## zh_silver_23

- REF: 器官捐献与移植是一个复杂但充满希望的医疗流程。当一个人不幸去世，但他的身体器官功能良好时，他的家人可以选择捐献这些器官。这个决定需要经过一个严格的医疗流程。首先，医生会评估捐献者是否适合捐献，以及哪些器官可以捐献。

- REP: 器官捐献与移植是一只复杂但充满希望的医疗流程。当一个人不幸去世，但他的身体器官功能良好时，他的家人可以选择捐献这些器官。这个决定需要经过一个严格的医疗流程。首先，医生会评估捐献者是否适合过捐献，以及哪些器官可以捐献。

- Draft errors: [{"span_repro": [8, 22], "span_ref": [8, 22], "subtype": "classifier", "subtype_v5_target": "classifier", "severity_v2": "major", "learner_form": "一只复杂但充满希望的医疗流程", "corrected_form": "一个复杂但充满希望的医疗流程"}, {"span_repro": [89, 96], "span_ref": [89, 95], "subtype": "aspect_marker", "subtype_v5_target": "aspect_marker", "severity_v2": "major", "learner_form": "是否适合过捐献", "corrected_form": "是否适合捐献"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "是一只复杂但充满希望的医疗流程", "corrected_form": "是一个复杂但充满希望的医疗流程", "subtype": "classifier", "severity": "minor"}, {"learner_form": "是否适合过捐献", "corrected_form": "是否适合捐献", "subtype": "aspect_marker", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: wrong classifier 只 for 流程; spurious experiential aspect 过 inserted, confusing tense/meaning

- Why dropped: severity mismatch on '一只复杂但充满希望的医疗流程': draft=major reviewer=minor



## zh_silver_24

- REF: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，捐献过程就会立即开始。

- REP: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，立即捐献过程就会开始。

- Draft errors: [{"span_repro": [91, 101], "span_ref": [91, 101], "subtype": "adverbial_order", "subtype_v5_target": "adverbial_order", "severity_v2": "major", "learner_form": "立即捐献过程就会开始", "corrected_form": "捐献过程就会立即开始"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "立即捐献过程就会开始", "corrected_form": "捐献过程就会立即开始", "subtype": "adverbial_order", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 立即 misplaced to sentence-initial position, still grammatical but less idiomatic

- Why dropped: severity mismatch on '立即捐献过程就会开始': draft=major reviewer=minor



## zh_silver_25

- REF: 整个器官捐献与移植的流程，从捐献者的决定到受者的康复，都体现了生命的延续和人道的关怀。这个过程需要多方协作，包括捐献者家属、医疗团队、患者以及社会的支持。

- REP: 整个器官捐献与移植的流程，都体现了生命的延续和人道的关怀，从捐献者的决定到受者的康复。这个过程需要多方协作，包括捐献者家属、医疗团队、患者以及社会的支持。

- Draft errors: [{"span_repro": [13, 42], "span_ref": [13, 42], "subtype": "adverbial_order", "subtype_v5_target": "adverbial_order", "severity_v2": "major", "learner_form": "都体现了生命的延续和人道的关怀，从捐献者的决定到受者的康复", "corrected_form": "从捐献者的决定到受者的康复，都体现了生命的延续和人道的关怀"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "都体现了生命的延续和人道的关怀，从捐献者的决定到受者的康复", "corrected_form": "从捐献者的决定到受者的康复，都体现了生命的延续和人道的关怀", "subtype": "word_order", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 从...到... clause moved from modifying 流程 to trailing the sentence, changing its attachment and reading flow

- Why dropped: naturalness mismatch: draft=4 reviewer=3



## zh_silver_26

- REF: 我希望这件T恤能一直陪伴我，直到它变得非常非常旧，但即使那样，我也会把它好好收藏起来，作为一份美好的纪念。它的图案，那个微笑的小猫，永远是我心中最温暖的存在。

- REP: 我希望这件T恤能一直陪伴我，直到它变得非常非常旧，但即使那样，我也会把它收藏起来，作为一份美好的纪念。它的图案，那个微笑的小猫，永远是我心中最温暖的存在。

- Draft errors: [{"span_repro": [32, 40], "span_ref": [32, 42], "subtype": "omission", "subtype_v5_target": "omission", "severity_v2": "major", "learner_form": "也会把它收藏起来", "corrected_form": "也会把它好好收藏起来"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: []

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 好好 (manner adverb) dropped; optional intensifier, meaning and grammar intact, treated as acceptable variation

- Why dropped: error count mismatch: draft=1 reviewer=0



## zh_silver_27

- REF: 但是，当我想找一件最舒服、最能代表我心情的衣服时，我总是会选择这件蓝色的T恤，带着那个微笑的小猫图案。它不仅仅是一件衣服，更像是我心情的一个晴雨表，它总是能在我需要的时候，给我带来温暖和力量。这件T恤的图案，那只微笑的小猫，也让我联想到很多关于快乐和友谊的东西。小猫的笑容是那么纯真，那么有感染力。

- REP: 但是，当我想找一件最舒服、最能代表我心情的衣服时，我总是会选择这件蓝色的T恤，带着那个微笑的小猫图案。它不仅仅是一件衣服，更像是我心情的一个晴雨表，它总是能在我需要的时候，给我带来温暖和力量。那只微笑的小猫，这件T恤的图案，也让我联想到很多关于快乐和友谊的东西。小猫的笑容是那么纯真，那么有感染力。

- Draft errors: [{"span_repro": [96, 118], "span_ref": [96, 118], "subtype": "topic_comment", "subtype_v5_target": "topic_comment", "severity_v2": "minor", "learner_form": "那只微笑的小猫，这件T恤的图案，也让我联想到", "corrected_form": "这件T恤的图案，那只微笑的小猫，也让我联想到"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "那只微笑的小猫，这件T恤的图案，也让我联想到", "corrected_form": "这件T恤的图案，那只微笑的小猫，也让我联想到", "subtype": "word_order", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: order of the appositive pair reversed, mildly less natural

- Why dropped: subtype mismatch: draft=topic_comment reviewer=word_order (dims naturalness vs accuracy)



## zh_silver_28

- REF: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- REP: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在看着我，又据称在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- Draft errors: [{"span_repro": [62, 70], "span_ref": [62, 70], "subtype": "register", "subtype_v5_target": "register", "severity_v2": "major", "learner_form": "又据称在和我说话", "corrected_form": "又好像在和我说话"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "又据称在和我说话", "corrected_form": "又好像在和我说话", "subtype": "register", "severity": "major"}]

- Reviewer bands: naturalness=2 range=4

- Reviewer comment: 据称 (formal/reportative 'allegedly') is a severe register clash in a whimsical description of a cat's expression

- Why dropped: naturalness mismatch: draft=4 reviewer=2



## zh_silver_29

- REF: 那天，我跑来跑去，和小猫图案一样开心。我还记得有一次，在学校里，我的朋友们都夸我的T恤很可爱，我们一起分享了喜欢的卡通人物。这件T恤就像一个老朋友，陪伴我度过了很多快乐的时光。有时候，我会在家里，只是穿着这件T恤，看看书，听听音乐。

- REP: 那天，我跑来跑去，和小猫图案一样开心。我还记得有一次，在学校里，我地朋友们都夸我的T恤很可爱，我们一起分享了喜欢的卡通人物。这件T恤就像一个老朋友，陪伴我度过了很多快乐的时光。有时候，我会在家里，只是穿着这件T恤，看看书，听听音乐。

- Draft errors: [{"span_repro": [32, 46], "span_ref": [32, 46], "subtype": "de_particles", "subtype_v5_target": "de_particles", "severity_v2": "minor", "learner_form": "我地朋友们都夸我的T恤很可爱", "corrected_form": "我的朋友们都夸我的T恤很可爱"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "我地朋友们都夸", "corrected_form": "我的朋友们都夸", "subtype": "de_particles", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 的/地 confusion (possessive marker written as adverbial marker)

- Why dropped: naturalness mismatch: draft=4 reviewer=3



## zh_silver_31

- REF: 它让我感到很放松，很自在。它不像那些需要精心搭配的衣服，穿上它，我就能立刻出门，去做我想做的事情。它的简单和舒适，让我觉得很安心。当然，我也有其他漂亮的衣服，有适合参加派对的，有适合上班的。

- REP: 它让我感到很放松，很自在。它不像那些应该被精心搭配好的衣服，穿上它，我就能立刻出门，去做我想做的事情。它的简单和舒适，让我觉得很安心。当然，我也有其他漂亮的衣服，有适合参加派对的，有适合上班的。

- Draft errors: [{"span_repro": [16, 29], "span_ref": [16, 27], "subtype": "bei_passive", "subtype_v5_target": "bei_passive", "severity_v2": "minor", "learner_form": "那些应该被精心搭配好的衣服", "corrected_form": "那些需要精心搭配的衣服"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "不像那些应该被精心搭配好的衣服", "corrected_form": "不像那些需要精心搭配的衣服", "subtype": "addition", "severity": "minor"}]

- Reviewer bands: naturalness=2 range=4

- Reviewer comment: 应该被...好 added, producing verbose, translated-sounding phrasing

- Why dropped: subtype mismatch: draft=bei_passive reviewer=addition (dims accuracy vs fidelity)



## zh_silver_32

- REF: 它提醒我，生活中有很多简单而美好的事物值得我们去发现和珍惜。每次看到它，我都会想起那些无忧无虑的日子，想起那些真心对我好的人。所以，尽管它只是一件普通的T恤，但对我来说，它有着非凡的意义。它是我的“最喜欢的”衣服，因为它代表着舒适、快乐和珍贵的回忆。

- REP: 它提醒我，生活中有很多简单而美好的事物值得我们去发现和珍惜。每次看到它，我都会想起那些无忧无虑的日子，想起那些真心对我好的人。所以，尽管它只是一件普通的T恤，但对我来说，它有着非凡的意义。它是我的“最喜欢的”衣服，因为它代表的其实是舒适、快乐和珍贵的回忆。

- Draft errors: [{"span_repro": [107, 118], "span_ref": [107, 115], "subtype": "addition", "subtype_v5_target": "addition", "severity_v2": "minor", "learner_form": "因为它代表的其实是舒适", "corrected_form": "因为它代表着舒适"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "它代表的其实是舒适、快乐和珍贵的回忆", "corrected_form": "它代表着舒适、快乐和珍贵的回忆", "subtype": "addition", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 其实 added, introducing an unwarranted corrective/contrastive nuance not in the reference

- Why dropped: no learner_form match for draft error '因为它代表的其实是舒适' (subtype addition)



## zh_silver_33

- REF: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植到患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- REP: 捐献的器官会在手术中被小心地取出，并被迅速地运送到需要进行移植手术的医院。移植手术本身也是一个精密的医疗过程，由经验丰富的外科医生团队执行。医生会将捐献的健康器官移植患者体内，替换掉功能衰竭的器官。移植手术后，受者需要接受长期的医疗护理和药物治疗，以确保新器官能够正常工作，并防止身体排斥它。

- Draft errors: [{"span_repro": [81, 87], "span_ref": [81, 88], "subtype": "directional_complement", "subtype_v5_target": "directional_complement", "severity_v2": "major", "learner_form": "移植患者体内", "corrected_form": "移植到患者体内"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "移植患者体内", "corrected_form": "移植到患者体内", "subtype": "directional_complement", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 到 dropped, leaving 移植患者体内 ungrammatical/ambiguous

- Why dropped: naturalness mismatch: draft=4 reviewer=3



## zh_silver_34

- REF: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个小小的、很可爱的图画。这个图画是一只正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- REP: 这件T恤最特别的地方是它的图案。在T恤的胸口位置，有一个图画小小的、很可爱的。这个图画是一只正在微笑的小猫，它好像在看着我，又好像在和我说话。小猫的眼睛是圆圆的，带着一点点好奇，它的嘴角微微向上翘起，看起来非常开心。

- Draft errors: [{"span_repro": [25, 38], "span_ref": [25, 38], "subtype": "word_order", "subtype_v5_target": "word_order", "severity_v2": "major", "learner_form": "有一个图画小小的、很可爱的", "corrected_form": "有一个小小的、很可爱的图画"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "有一个图画小小的、很可爱的", "corrected_form": "有一个小小的、很可爱的图画", "subtype": "word_order", "severity": "major"}]

- Reviewer bands: naturalness=2 range=4

- Reviewer comment: noun 图画 moved before its own modifiers, breaking standard attributive order, requires rereading

- Why dropped: naturalness mismatch: draft=4 reviewer=2



## zh_silver_36

- REF: 整个器官捐献与移植的流程，从捐献者的决定到受者的康复，都体现了生命的延续和人道的关怀。这个过程需要多方协作，包括捐献者家属、医疗团队、患者以及社会的支持。

- REP: 整个器官捐献与移植的流程，从捐献者的决定到受者的康复，都体现过生命的延续和人道的关怀。这个过程需要多方协作，包括捐献者家属、医疗团队、患者以及社会的支持。

- Draft errors: [{"span_repro": [27, 36], "span_ref": [27, 36], "subtype": "aspect_marker", "subtype_v5_target": "aspect_marker", "severity_v2": "major", "learner_form": "都体现过生命的延续", "corrected_form": "都体现了生命的延续"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "都体现过生命的延续", "corrected_form": "都体现了生命的延续", "subtype": "aspect_marker", "severity": "minor"}]

- Reviewer bands: naturalness=4 range=4

- Reviewer comment: 了->过 aspect marker misuse (matches gold zh_seed_03 pattern)

- Why dropped: severity mismatch on '都体现过生命的延续': draft=major reviewer=minor



## zh_silver_37

- REF: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却栩栩如生，充满了生命力。我每次看到这个图案，都会觉得心情变好。我喜欢这件T恤，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。我记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- REP: 猫咪的毛发画得很细致，虽然只是一个简单的图案，但却栩栩如生，充满了生命力。我每次看到这个图案，都会把心情变好。我喜欢这件T恤，不仅仅是因为它的颜色和图案，更是因为它承载了很多美好的回忆。我记得第一次穿这件T恤是在一个阳光明媚的周末，我和家人一起去公园野餐。

- Draft errors: [{"span_repro": [47, 54], "span_ref": [47, 55], "subtype": "ba_construction", "subtype_v5_target": "ba_construction", "severity_v2": "major", "learner_form": "都会把心情变好", "corrected_form": "都会觉得心情变好"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "都会把心情变好", "corrected_form": "都会觉得心情变好", "subtype": "word_choice", "severity": "minor"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 觉得 (feel) replaced by a 把-causative construction; grammatical but shifts from involuntary feeling to deliberate causation

- Why dropped: subtype mismatch: draft=ba_construction reviewer=word_choice (dims accuracy vs fidelity)



## zh_silver_38

- REF: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找到匹配的受者，捐献过程就会立即开始。

- REP: 如果条件符合，这些信息会被记录下来。与此同时，有许多患者正等待着器官移植来挽救生命。医疗系统会根据患者的身体状况、血型以及配型情况，在等待名单中寻找最合适的受者。一旦找匹配的受者，捐献过程就会立即开始。

- Draft errors: [{"span_repro": [81, 89], "span_ref": [81, 90], "subtype": "resultative_complement", "subtype_v5_target": "resultative_complement", "severity_v2": "major", "learner_form": "一旦找匹配的受者", "corrected_form": "一旦找到匹配的受者"}]

- Draft bands: naturalness=4 range=4

- Reviewer errors: [{"learner_form": "一旦找匹配的受者", "corrected_form": "一旦找到匹配的受者", "subtype": "resultative_complement", "severity": "major"}]

- Reviewer bands: naturalness=3 range=4

- Reviewer comment: 到 (resultative, 'successfully') dropped from 找到; weakens the logical link to the following 'process begins immediately'

- Why dropped: naturalness mismatch: draft=4 reviewer=3


