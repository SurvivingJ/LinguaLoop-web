# Author brief 03 — en -> zh, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/docs/<test_id>.zh.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/en/sentencewise --tests fb2ceec5-88da-47cb-8296-1bc07dfb8eae,158a4f82-11f1-487e-bfeb-d85e2a9e9ad6,29c97a40-63fb-4399-bd9e-8e08a068c332,c873cef5-3208-4658-bdd6-ee56a72ef66c,a139fcae-55da-487e-ad0d-264992cf700b,f95ed2c2-2ba4-479b-831c-32fb8df05350`
and fix until every test is `ok`.

## fb2ceec5-88da-47cb-8296-1bc07dfb8eae — Leo and His Sports First Aid Kit

Passage (for context, do not translate as a block unless the arm says so):

Leo plays soccer with his friends every week. Sometimes, kids fall down and get small injuries when they run fast. To help, Leo has a special red box called a first aid kit. He keeps it in his sports bag. Inside the kit, there are clean bandages to stop blood and cold packs to make a bumped knee feel better. Leo brings this kit to every game so he can help his team stay safe and happy.

Sentences:

- idx 0: Leo plays soccer with his friends every week.
- idx 1: Sometimes, kids fall down and get small injuries when they run fast.
- idx 2: To help, Leo has a special red box called a first aid kit.
- idx 3: He keeps it in his sports bag.
- idx 4: Inside the kit, there are clean bandages to stop blood and cold packs to make a bumped knee feel better.
- idx 5: Leo brings this kit to every game so he can help his team stay safe and happy.

## 158a4f82-11f1-487e-bfeb-d85e2a9e9ad6 — Engineering Wonders: How Ancient Rome Brought Water to the City

Passage (for context, do not translate as a block unless the arm says so):

Long ago, people in the old Roman city needed water. They lived far from the river. They made a smart plan to bring water to their homes. Workers built long lines of stone. This big engineering work helped move water from far away. The water went through deep holes in the hills. It also crossed high stone bridges. Water moved inside these paths every day. It went down slowly because the ground tilted. No pumps were used. The natural shape of the land pushed the water forward. This great infrastructure changed daily life. Clean water came right to the town. People used it to drink, cook, and wash. The smart design kept the city alive and well.

Sentences:

- idx 0: Long ago, people in the old Roman city needed water.
- idx 1: They lived far from the river.
- idx 2: They made a smart plan to bring water to their homes.
- idx 3: Workers built long lines of stone.
- idx 4: This big engineering work helped move water from far away.
- idx 5: The water went through deep holes in the hills.
- idx 6: It also crossed high stone bridges.
- idx 7: Water moved inside these paths every day.
- idx 8: It went down slowly because the ground tilted.
- idx 9: No pumps were used.
- idx 10: The natural shape of the land pushed the water forward.
- idx 11: This great infrastructure changed daily life.
- idx 12: Clean water came right to the town.
- idx 13: People used it to drink, cook, and wash.
- idx 14: The smart design kept the city alive and well.

## 29c97a40-63fb-4399-bd9e-8e08a068c332 — Building Things with a 3D Printer

Passage (for context, do not translate as a block unless the arm says so):

A makerspace is a fun room for new technology. People go there to build things. A 3D printing machine is a cool tool in this room. First, you make a design on a computer. The computer tells the printer what to shape. Then, the printer works in a special way. Traditional manufacturing cuts big pieces down. But 3D printing builds things up from the bottom. The machine puts down tiny lines of hot plastic. It adds one layer on top of another layer. The plastic cools down fast and gets hard. Soon, a new toy or cup is ready!

Sentences:

- idx 0: A makerspace is a fun room for new technology.
- idx 1: People go there to build things.
- idx 2: A 3D printing machine is a cool tool in this room.
- idx 3: First, you make a design on a computer.
- idx 4: The computer tells the printer what to shape.
- idx 5: Then, the printer works in a special way.
- idx 6: Traditional manufacturing cuts big pieces down.
- idx 7: But 3D printing builds things up from the bottom.
- idx 8: The machine puts down tiny lines of hot plastic.
- idx 9: It adds one layer on top of another layer.
- idx 10: The plastic cools down fast and gets hard.
- idx 11: Soon, a new toy or cup is ready!

## c873cef5-3208-4658-bdd6-ee56a72ef66c — How Music Notes Were Born

Passage (for context, do not translate as a block unless the arm says so):

Long ago, people made music. They sang songs. They played instruments. But they did not write music down. It was hard to remember songs. Then, people wanted to write music. They started to draw marks. These marks helped them remember notes. This was the start of music notation. Over history, this system grew. It helped composers write more music. They could share their ideas. The marks became clearer. They showed how high or low a sound should be. They also showed how long a sound should last. This development in notation made music richer. It helped music grow over time. The history of music is tied to how we write it.

Sentences:

- idx 0: Long ago, people made music.
- idx 1: They sang songs.
- idx 2: They played instruments.
- idx 3: But they did not write music down.
- idx 4: It was hard to remember songs.
- idx 5: Then, people wanted to write music.
- idx 6: They started to draw marks.
- idx 7: These marks helped them remember notes.
- idx 8: This was the start of music notation.
- idx 9: Over history, this system grew.
- idx 10: It helped composers write more music.
- idx 11: They could share their ideas.
- idx 12: The marks became clearer.
- idx 13: They showed how high or low a sound should be.
- idx 14: They also showed how long a sound should last.
- idx 15: This development in notation made music richer.
- idx 16: It helped music grow over time.
- idx 17: The history of music is tied to how we write it.

## a139fcae-55da-487e-ad0d-264992cf700b — Green Cities, Good Life

Passage (for context, do not translate as a block unless the arm says so):

Green parks help cities. Trees make the air good. People like to walk in parks. Parks make houses look nice. This helps **real estate**. Also, we can grow food in the city. This is **vertical farming**. It helps with **food security**. We do not need to bring food from far away. This is good for the planet. This is **sustainability**. Cities need to plan well. This is **urban planning**. Putting money into green things is a good **investment**.

Sentences:

- idx 0: Green parks help cities.
- idx 1: Trees make the air good.
- idx 2: People like to walk in parks.
- idx 3: Parks make houses look nice.
- idx 4: This helps **real estate**.
- idx 5: Also, we can grow food in the city.
- idx 6: This is **vertical farming**.
- idx 7: It helps with **food security**.
- idx 8: We do not need to bring food from far away.
- idx 9: This is good for the planet.
- idx 10: This is **sustainability**.
- idx 11: Cities need to plan well.
- idx 12: This is **urban planning**.
- idx 13: Putting money into green things is a good **investment**.

## f95ed2c2-2ba4-479b-831c-32fb8df05350 — Clothes Use Much Water

Passage (for context, do not translate as a block unless the arm says so):

Cotton plants need much water to grow. Many clothes are made from cotton. This uses a lot of water. Water is very important. Some places do not have enough water. This is called water scarcity. Making clothes can make water dirty. This bad water is pollution. People buy many new clothes. This is consumerism. The clothes come from far away. This is the supply chain. It uses more water. We can help. Buy fewer new clothes.

Sentences:

- idx 0: Cotton plants need much water to grow.
- idx 1: Many clothes are made from cotton.
- idx 2: This uses a lot of water.
- idx 3: Water is very important.
- idx 4: Some places do not have enough water.
- idx 5: This is called water scarcity.
- idx 6: Making clothes can make water dirty.
- idx 7: This bad water is pollution.
- idx 8: People buy many new clothes.
- idx 9: This is consumerism.
- idx 10: The clothes come from far away.
- idx 11: This is the supply chain.
- idx 12: It uses more water.
- idx 13: We can help.
- idx 14: Buy fewer new clothes.
