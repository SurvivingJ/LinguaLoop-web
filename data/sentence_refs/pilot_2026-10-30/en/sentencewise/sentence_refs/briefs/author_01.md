# Author brief 01 — en -> zh, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/docs/<test_id>.zh.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/en/sentencewise --tests 7f9c347a-8a9b-410f-8a04-8271664b8da8,c6e32430-9b41-447e-bc8e-775d75e0b798,26c33b80-8149-4373-849d-72d50b0f784c,c008fc7a-d475-429d-8963-de3e8e763b39,97f5efe0-23cf-4c8d-8bf1-c91a8b3b6de5,8bd36dd0-91c3-475b-811d-eb1a9fc02ac8`
and fix until every test is `ok`.

## 7f9c347a-8a9b-410f-8a04-8271664b8da8 — Clean Air, Happy Earth

Passage (for context, do not translate as a block unless the arm says so):

Cars make the air dirty. This is pollution. Many cars make more pollution. We can take a bus. A bus is big. Many people ride the bus. This is good for the air. Less cars mean less pollution. People can walk to places. They can ride a bike too. This helps the Earth. It is a good way to go. We can help the Earth.

Sentences:

- idx 0: Cars make the air dirty.
- idx 1: This is pollution.
- idx 2: Many cars make more pollution.
- idx 3: We can take a bus.
- idx 4: A bus is big.
- idx 5: Many people ride the bus.
- idx 6: This is good for the air.
- idx 7: Less cars mean less pollution.
- idx 8: People can walk to places.
- idx 9: They can ride a bike too.
- idx 10: This helps the Earth.
- idx 11: It is a good way to go.
- idx 12: We can help the Earth.

## c6e32430-9b41-447e-bc8e-775d75e0b798 — Your Robot Friend

Passage (for context, do not translate as a block unless the arm says so):

A robot friend can help you. It can do many things. This robot is smart. It can learn new things. It can help with your work. It can play with you. It is like a good friend. It can work on your own computer. This is good. It can help you. People can use it. It can help many people. It can do what you want. It is a good helper.

Sentences:

- idx 0: A robot friend can help you.
- idx 1: It can do many things.
- idx 2: This robot is smart.
- idx 3: It can learn new things.
- idx 4: It can help with your work.
- idx 5: It can play with you.
- idx 6: It is like a good friend.
- idx 7: It can work on your own computer.
- idx 8: This is good.
- idx 9: It can help you.
- idx 10: People can use it.
- idx 11: It can help many people.
- idx 12: It can do what you want.
- idx 13: It is a good helper.

## 26c33b80-8149-4373-849d-72d50b0f784c — How to Wash Your Hands

Passage (for context, do not translate as a block unless the arm says so):

Look at your hands. Tiny germs live on them. You cannot see the germs. You must wash your hands. Go to the sink. Put water on your hands. Take the soap. Rub the soap on your hands. Make lots of bubbles. The soap kills the bad germs. Now, wash the soap off with water. Use a towel to dry your hands. Your hands are clean now!

Sentences:

- idx 0: Look at your hands.
- idx 1: Tiny germs live on them.
- idx 2: You cannot see the germs.
- idx 3: You must wash your hands.
- idx 4: Go to the sink.
- idx 5: Put water on your hands.
- idx 6: Take the soap.
- idx 7: Rub the soap on your hands.
- idx 8: Make lots of bubbles.
- idx 9: The soap kills the bad germs.
- idx 10: Now, wash the soap off with water.
- idx 11: Use a towel to dry your hands.
- idx 12: Your hands are clean now!

## c008fc7a-d475-429d-8963-de3e8e763b39 — Coffee Beans Travel the World

Passage (for context, do not translate as a block unless the arm says so):

A bean grows on a plant. This is a coffee bean. People pick the beans. They put them in bags. These bags go on big boats. The boats move far away. One country sells beans to another country. This is called export. Another country buys the beans. This is called import. People in this new country want to drink coffee. They buy the coffee. Many people drink coffee. This is called consumption. This is how beans trade. It is part of farming.

Sentences:

- idx 0: A bean grows on a plant.
- idx 1: This is a coffee bean.
- idx 2: People pick the beans.
- idx 3: They put them in bags.
- idx 4: These bags go on big boats.
- idx 5: The boats move far away.
- idx 6: One country sells beans to another country.
- idx 7: This is called export.
- idx 8: Another country buys the beans.
- idx 9: This is called import.
- idx 10: People in this new country want to drink coffee.
- idx 11: They buy the coffee.
- idx 12: Many people drink coffee.
- idx 13: This is called consumption.
- idx 14: This is how beans trade.
- idx 15: It is part of farming.

## 97f5efe0-23cf-4c8d-8bf1-c91a8b3b6de5 — Time and Places

Passage (for context, do not translate as a block unless the arm says so):

People see time in different ways. Some people like to be on time. They like to do things when they plan. They make a plan for the day. This is like knowing when to eat lunch. Other people do not worry much about time. They can wait to do things. They can be late. This is okay for them. It is a cultural difference. This means how people in different places think. This is important when we meet people from other lands.

Sentences:

- idx 0: People see time in different ways.
- idx 1: Some people like to be on time.
- idx 2: They like to do things when they plan.
- idx 3: They make a plan for the day.
- idx 4: This is like knowing when to eat lunch.
- idx 5: Other people do not worry much about time.
- idx 6: They can wait to do things.
- idx 7: They can be late.
- idx 8: This is okay for them.
- idx 9: It is a cultural difference.
- idx 10: This means how people in different places think.
- idx 11: This is important when we meet people from other lands.

## 8bd36dd0-91c3-475b-811d-eb1a9fc02ac8 — Composting: Easy Garden Dirt

Passage (for context, do not translate as a block unless the arm says so):

We can make good things for our garden. This is good for the Earth. We can use old food. We can use old leaves. This is called composting. It is a way for waste reduction. We put these things in a bin. The bin is for compost. It helps plants grow. Plants are organic. We can do this DIY. It is easy to start. We put food scraps in. We put yard waste in. Then, we wait. The food and leaves break down. They make dark dirt. This dirt is good for the garden. It helps our plants. It is a good way to help nature.

Sentences:

- idx 0: We can make good things for our garden.
- idx 1: This is good for the Earth.
- idx 2: We can use old food.
- idx 3: We can use old leaves.
- idx 4: This is called composting.
- idx 5: It is a way for waste reduction.
- idx 6: We put these things in a bin.
- idx 7: The bin is for compost.
- idx 8: It helps plants grow.
- idx 9: Plants are organic.
- idx 10: We can do this DIY.
- idx 11: It is easy to start.
- idx 12: We put food scraps in.
- idx 13: We put yard waste in.
- idx 14: Then, we wait.
- idx 15: The food and leaves break down.
- idx 16: They make dark dirt.
- idx 17: This dirt is good for the garden.
- idx 18: It helps our plants.
- idx 19: It is a good way to help nature.
