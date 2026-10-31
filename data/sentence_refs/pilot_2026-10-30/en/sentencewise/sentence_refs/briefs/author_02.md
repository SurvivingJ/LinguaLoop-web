# Author brief 02 — en -> zh, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/docs/<test_id>.zh.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/en/sentencewise --tests 2ef4d908-2ac6-40d1-a067-f205ca8e37c0,a43d4b63-d66a-4ae6-ac27-61986c4af9ed,16159b92-a62d-4b67-aa99-6a878d3d9987,f28ad01a-6ebe-4c00-9d23-232b70e452da,f388bd16-eed7-4600-a86d-52aa21646734,ddb8c17f-b517-4a5f-a4db-3debcae46db0`
and fix until every test is `ok`.

## 2ef4d908-2ac6-40d1-a067-f205ca8e37c0 — Online Games: Fun Together

Passage (for context, do not translate as a block unless the arm says so):

People play games on the internet. They play in virtual worlds. This is fun. Sometimes they play with friends. They do teamwork. They help each other. This is collaboration. They want to win. They work together. This is good teamwork. Sometimes people play against each other. This is competition. They try to be the best. They play games. They sit at home and play. They use a computer. It is a fun game.

Sentences:

- idx 0: People play games on the internet.
- idx 1: They play in virtual worlds.
- idx 2: This is fun.
- idx 3: Sometimes they play with friends.
- idx 4: They do teamwork.
- idx 5: They help each other.
- idx 6: This is collaboration.
- idx 7: They want to win.
- idx 8: They work together.
- idx 9: This is good teamwork.
- idx 10: Sometimes people play against each other.
- idx 11: This is competition.
- idx 12: They try to be the best.
- idx 13: They play games.
- idx 14: They sit at home and play.
- idx 15: They use a computer.
- idx 16: It is a fun game.

## a43d4b63-d66a-4ae6-ac27-61986c4af9ed — Stories Are Our Friends

Passage (for context, do not translate as a block unless the arm says so):

People tell stories. They tell stories to friends. They tell stories to family. Stories are like pictures in the head. Stories help us learn. They help us remember. Long ago, people told stories. It was their way to share news. It was their way to teach. These old stories are like friends. They help us know about the past. They show us how people lived. Stories are important for everyone. They help us talk and play.

Sentences:

- idx 0: People tell stories.
- idx 1: They tell stories to friends.
- idx 2: They tell stories to family.
- idx 3: Stories are like pictures in the head.
- idx 4: Stories help us learn.
- idx 5: They help us remember.
- idx 6: Long ago, people told stories.
- idx 7: It was their way to share news.
- idx 8: It was their way to teach.
- idx 9: These old stories are like friends.
- idx 10: They help us know about the past.
- idx 11: They show us how people lived.
- idx 12: Stories are important for everyone.
- idx 13: They help us talk and play.

## 16159b92-a62d-4b67-aa99-6a878d3d9987 — The Story of the Recycling Arrows

Passage (for context, do not translate as a block unless the arm says so):

A man saw old things. He wanted to use them again. This was a good idea. He made a special picture. It has three arrows. It is like a triangle. The arrows go around. This picture means good things. It means not throwing things out. It means using things again. People saw the picture. They liked it. It is about helping the Earth. It is about being clean. Many places use this picture now. It is for paper. It is for plastic. It is for glass. This picture is on many things we use. It helps us know we can use them again. This is good for everyone. It is a smart design. It shows us what to do. It is part of our clean world.

Sentences:

- idx 0: A man saw old things.
- idx 1: He wanted to use them again.
- idx 2: This was a good idea.
- idx 3: He made a special picture.
- idx 4: It has three arrows.
- idx 5: It is like a triangle.
- idx 6: The arrows go around.
- idx 7: This picture means good things.
- idx 8: It means not throwing things out.
- idx 9: It means using things again.
- idx 10: People saw the picture.
- idx 11: They liked it.
- idx 12: It is about helping the Earth.
- idx 13: It is about being clean.
- idx 14: Many places use this picture now.
- idx 15: It is for paper.
- idx 16: It is for plastic.
- idx 17: It is for glass.
- idx 18: This picture is on many things we use.
- idx 19: It helps us know we can use them again.
- idx 20: This is good for everyone.
- idx 21: It is a smart design.
- idx 22: It shows us what to do.
- idx 23: It is part of our clean world.

## f28ad01a-6ebe-4c00-9d23-232b70e452da — Plastic Bag Rules

Passage (for context, do not translate as a block unless the arm says so):

Some places make rules. These rules stop people from using some bags. The bags are made of plastic. Plastic bags go in the trash. Too much trash is bad. It makes the world messy. Other places have rules too. These rules help the earth. People try to use less plastic. This is a new way. It is good for the world.

Sentences:

- idx 0: Some places make rules.
- idx 1: These rules stop people from using some bags.
- idx 2: The bags are made of plastic.
- idx 3: Plastic bags go in the trash.
- idx 4: Too much trash is bad.
- idx 5: It makes the world messy.
- idx 6: Other places have rules too.
- idx 7: These rules help the earth.
- idx 8: People try to use less plastic.
- idx 9: This is a new way.
- idx 10: It is good for the world.

## f388bd16-eed7-4600-a86d-52aa21646734 — From Windmills to Sun Power

Passage (for context, do not translate as a block unless the arm says so):

People need power. They used wind long ago. Big arms went round and round. This made power. It was good for the town. Now, we have new ways. We have sun power. Big flat things catch the sun. The sun makes power for homes. This is clean energy. It is good for the air. This technology is a big change. It helps our world. The history of power is long. People keep finding new ways. This helps us all. We want to make power that is clean. Our new ideas help. This is an innovation.

Sentences:

- idx 0: People need power.
- idx 1: They used wind long ago.
- idx 2: Big arms went round and round.
- idx 3: This made power.
- idx 4: It was good for the town.
- idx 5: Now, we have new ways.
- idx 6: We have sun power.
- idx 7: Big flat things catch the sun.
- idx 8: The sun makes power for homes.
- idx 9: This is clean energy.
- idx 10: It is good for the air.
- idx 11: This technology is a big change.
- idx 12: It helps our world.
- idx 13: The history of power is long.
- idx 14: People keep finding new ways.
- idx 15: This helps us all.
- idx 16: We want to make power that is clean.
- idx 17: Our new ideas help.
- idx 18: This is an innovation.

## ddb8c17f-b517-4a5f-a4db-3debcae46db0 — Open AI: Showing How Programs Learn

Passage (for context, do not translate as a block unless the arm says so):

A company makes computer programs. These programs learn things. People give the programs data to learn. This data is like a book. The company must tell people what is in the book. They must show how the program learns. It is like showing how a child learns. The company needs to be safe. They must follow rules. The rules help people. People want to know what the program knows. They want to know how the program thinks. This is not a secret. The company shows them. If the company does not show, people can be sad. They might not trust the program. It is good to be open. It makes the program feel good. Everyone can feel good with the program. This is how the company works now.

Sentences:

- idx 0: A company makes computer programs.
- idx 1: These programs learn things.
- idx 2: People give the programs data to learn.
- idx 3: This data is like a book.
- idx 4: The company must tell people what is in the book.
- idx 5: They must show how the program learns.
- idx 6: It is like showing how a child learns.
- idx 7: The company needs to be safe.
- idx 8: They must follow rules.
- idx 9: The rules help people.
- idx 10: People want to know what the program knows.
- idx 11: They want to know how the program thinks.
- idx 12: This is not a secret.
- idx 13: The company shows them.
- idx 14: If the company does not show, people can be sad.
- idx 15: They might not trust the program.
- idx 16: It is good to be open.
- idx 17: It makes the program feel good.
- idx 18: Everyone can feel good with the program.
- idx 19: This is how the company works now.
