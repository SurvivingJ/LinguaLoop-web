# Author brief 04 — en -> zh, arm `sentencewise`

Read `data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/rules_authoring.md` first. Write one file per test under
`data/sentence_refs/pilot_2026-10-30/en/sentencewise/sentence_refs/docs/<test_id>.zh.json` in the shape the rules give.

Then run: `PYTHONIOENCODING=utf-8 python scripts/sentence_ref_runner.py check data/sentence_refs/pilot_2026-10-30/en/sentencewise --tests 3ddb9c3a-494b-45cb-8a74-610e95be311a,68b1b057-d97f-4386-a018-1073860df1bc,ae1d02c2-45c6-48f5-a634-c5c7c751a98c,dfe9265b-56b5-4843-ab5c-763325320ee0,0b39ed43-18c6-4c9c-977b-c2fc4837415f,97330b8b-31d2-42c3-bdb4-e33b13571639`
and fix until every test is `ok`.

## 3ddb9c3a-494b-45cb-8a74-610e95be311a — Good App Training Data

Passage (for context, do not translate as a block unless the arm says so):

A company makes a helpful app. It helps people learn new things. The app uses big lists of words. These lists help the app know what to teach. People give the app words to learn. This is "training data." The app must be good. It must not cheat. The company must tell people about the words. This is "disclosure." The app must show how it learns. This is "transparency." The company must be good and fair. They want people to like the app.

Sentences:

- idx 0: A company makes a helpful app.
- idx 1: It helps people learn new things.
- idx 2: The app uses big lists of words.
- idx 3: These lists help the app know what to teach.
- idx 4: People give the app words to learn.
- idx 5: This is "training data." The app must be good.
- idx 6: It must not cheat.
- idx 7: The company must tell people about the words.
- idx 8: This is "disclosure." The app must show how it learns.
- idx 9: This is "transparency." The company must be good and fair.
- idx 10: They want people to like the app.

## 68b1b057-d97f-4386-a018-1073860df1bc — Leo's Safe Afternoon Bicycle Journey to the Community Park

Passage (for context, do not translate as a block unless the arm says so):

Leo wheeled his blue bicycle out of the garage and prepared for the afternoon journey. Before he set off, he secured his helmet properly, recognizing that safety remained paramount whenever he rode. The afternoon sun cast long shadows across the neighborhood pavement as he pushed off and began to pedal toward the community park. Navigating the familiar route required attentive steering, especially near the busy intersection where cars often passed by. Leo signaled his turns clearly and stopped at the crosswalk to ensure the path was completely clear. Once he crossed safely, he accelerated down the gentle hill that led straight to the park entrance. Upon arrival, he parked his bike near the large oak tree and locked the frame securely. The park was filled with the lively sounds of children laughing and playing on the swings. Leo took a deep breath of the fresh air, glad that he had made the trip on two wheels, and walked over to join his friends on the grass.

Sentences:

- idx 0: Leo wheeled his blue bicycle out of the garage and prepared for the afternoon journey.
- idx 1: Before he set off, he secured his helmet properly, recognizing that safety remained paramount whenever he rode.
- idx 2: The afternoon sun cast long shadows across the neighborhood pavement as he pushed off and began to pedal toward the community park.
- idx 3: Navigating the familiar route required attentive steering, especially near the busy intersection where cars often passed by.
- idx 4: Leo signaled his turns clearly and stopped at the crosswalk to ensure the path was completely clear.
- idx 5: Once he crossed safely, he accelerated down the gentle hill that led straight to the park entrance.
- idx 6: Upon arrival, he parked his bike near the large oak tree and locked the frame securely.
- idx 7: The park was filled with the lively sounds of children laughing and playing on the swings.
- idx 8: Leo took a deep breath of the fresh air, glad that he had made the trip on two wheels, and walked over to join his friends on the grass.

## ae1d02c2-45c6-48f5-a634-c5c7c751a98c — Composting at Home: Your Green Guide to Sustainable Gardening

Passage (for context, do not translate as a block unless the arm says so):

Creating a home composting system is a fantastic step towards **sustainability** and **waste reduction**, especially for anyone interested in **gardening**. This **DIY** project allows you to transform your kitchen scraps and yard trimmings into rich, **organic** material that will nourish your plants. The fundamental principle behind composting is simple: microorganisms break down **organic** matter. To facilitate this process effectively, you need to provide them with the right conditions. A good compost bin can be purchased or you can easily build one yourself with a few planks of wood or even old pallets. The ideal location for your compost bin is a spot that gets some sun but is not completely exposed to harsh weather. It should also be easily accessible for adding materials and turning the compost. Balancing the "greens" and "browns" in your compost pile is crucial for success. "Greens" are nitrogen-rich materials like fruit and vegetable scraps, coffee grounds, and grass clippings. "Browns" are carbon-rich materials such as dry leaves, shredded newspaper, and cardboard. A general rule of thumb is to aim for a ratio of roughly two parts browns to one part greens. Too many greens can lead to a wet, smelly mess, while too many browns can slow down the decomposition process significantly. When adding kitchen scraps, avoid including meat, dairy products, or oily foods, as these can attract pests and create unpleasant odors. Grass clippings should be added in thin layers to prevent them from clumping together and becoming anaerobic. It's also a good idea to chop larger items into smaller pieces. This increases the surface area for the microorganisms to work on, speeding up decomposition. Turning your compost pile regularly is another key aspect. This process, often referred to as "aeration," introduces oxygen into the pile, which is essential for the aerobic bacteria that do the bulk of the decomposition work. Aim to turn it every week or two. You’ll know your compost is ready when it has a dark, crumbly texture and smells earthy, much like a forest floor after rain. This finished compost can then be spread around your garden beds, improving soil structure and providing vital nutrients for your plants, thus closing the loop on your **waste reduction** efforts and enhancing your **gardening** yields through truly **organic** means. It's a rewarding **DIY** endeavor that benefits both your garden and the planet by championing **sustainability**.

Sentences:

- idx 0: Creating a home composting system is a fantastic step towards **sustainability** and **waste reduction**, especially for anyone interested in **gardening**.
- idx 1: This **DIY** project allows you to transform your kitchen scraps and yard trimmings into rich, **organic** material that will nourish your plants.
- idx 2: The fundamental principle behind composting is simple: microorganisms break down **organic** matter.
- idx 3: To facilitate this process effectively, you need to provide them with the right conditions.
- idx 4: A good compost bin can be purchased or you can easily build one yourself with a few planks of wood or even old pallets.
- idx 5: The ideal location for your compost bin is a spot that gets some sun but is not completely exposed to harsh weather.
- idx 6: It should also be easily accessible for adding materials and turning the compost.
- idx 7: Balancing the "greens" and "browns" in your compost pile is crucial for success.
- idx 8: "Greens" are nitrogen-rich materials like fruit and vegetable scraps, coffee grounds, and grass clippings.
- idx 9: "Browns" are carbon-rich materials such as dry leaves, shredded newspaper, and cardboard.
- idx 10: A general rule of thumb is to aim for a ratio of roughly two parts browns to one part greens.
- idx 11: Too many greens can lead to a wet, smelly mess, while too many browns can slow down the decomposition process significantly.
- idx 12: When adding kitchen scraps, avoid including meat, dairy products, or oily foods, as these can attract pests and create unpleasant odors.
- idx 13: Grass clippings should be added in thin layers to prevent them from clumping together and becoming anaerobic.
- idx 14: It's also a good idea to chop larger items into smaller pieces.
- idx 15: This increases the surface area for the microorganisms to work on, speeding up decomposition.
- idx 16: Turning your compost pile regularly is another key aspect.
- idx 17: This process, often referred to as "aeration," introduces oxygen into the pile, which is essential for the aerobic bacteria that do the bulk of the decomposition work.
- idx 18: Aim to turn it every week or two.
- idx 19: You’ll know your compost is ready when it has a dark, crumbly texture and smells earthy, much like a forest floor after rain.
- idx 20: This finished compost can then be spread around your garden beds, improving soil structure and providing vital nutrients for your plants, thus closing the loop on your **waste reduction** efforts and enhancing your **gardening** yields through truly **organic** means.
- idx 21: It's a rewarding **DIY** endeavor that benefits both your garden and the planet by championing **sustainability**.

## dfe9265b-56b5-4843-ab5c-763325320ee0 — Unlocking Flight: The Physics Behind Airplanes

Passage (for context, do not translate as a block unless the arm says so):

The **physics** of how **airplanes** fly is a fascinating blend of **engineering** and natural forces. At its core, flight relies on the principle of **lift**, the upward force that counteracts gravity. This lift is primarily generated by the shape of an airplane's wings, often called airfoils. When air moves over the curved upper surface of a wing, it has to travel a longer distance than the air moving under the flatter bottom surface. To cover this longer distance in the same amount of time, the air above the wing moves faster. According to Bernoulli's principle, faster-moving air exerts less pressure than slower-moving air. Therefore, the pressure below the wing becomes greater than the pressure above, pushing the wing upwards, which is lift. Another crucial force is **drag**, which opposes the airplane's motion through the air. Drag is caused by air friction and the resistance of the air as the airplane moves through it. **Engineering** plays a vital role in minimizing drag by designing streamlined shapes for the aircraft's body and wings. The more streamlined the object, the less drag it experiences. Think of trying to push a flat board through water versus a sharp knife – the knife cuts through with less resistance. Similarly, airplanes are designed to "slice" through the air efficiently. The engines of an airplane provide thrust, a forward force that propels the aircraft, which in turn allows air to flow over the wings and generate lift. Without sufficient thrust, there wouldn't be enough airflow to create the pressure difference needed for lift. Once lift is greater than the weight of the airplane, it can take off and fly. Pilots constantly adjust the engine power and the position of control surfaces like ailerons and elevators to manage lift, drag, thrust, and weight, ensuring a stable and controlled flight. Understanding these fundamental **physics** principles is paramount for **engineering** safer and more efficient **airplanes**. It’s a continuous process of innovation, figuring out how to maximize **lift** and minimize **drag** for everything from small private jets to massive commercial airliners.

Sentences:

- idx 0: The **physics** of how **airplanes** fly is a fascinating blend of **engineering** and natural forces.
- idx 1: At its core, flight relies on the principle of **lift**, the upward force that counteracts gravity.
- idx 2: This lift is primarily generated by the shape of an airplane's wings, often called airfoils.
- idx 3: When air moves over the curved upper surface of a wing, it has to travel a longer distance than the air moving under the flatter bottom surface.
- idx 4: To cover this longer distance in the same amount of time, the air above the wing moves faster.
- idx 5: According to Bernoulli's principle, faster-moving air exerts less pressure than slower-moving air.
- idx 6: Therefore, the pressure below the wing becomes greater than the pressure above, pushing the wing upwards, which is lift.
- idx 7: Another crucial force is **drag**, which opposes the airplane's motion through the air.
- idx 8: Drag is caused by air friction and the resistance of the air as the airplane moves through it.
- idx 9: **Engineering** plays a vital role in minimizing drag by designing streamlined shapes for the aircraft's body and wings.
- idx 10: The more streamlined the object, the less drag it experiences.
- idx 11: Think of trying to push a flat board through water versus a sharp knife – the knife cuts through with less resistance.
- idx 12: Similarly, airplanes are designed to "slice" through the air efficiently.
- idx 13: The engines of an airplane provide thrust, a forward force that propels the aircraft, which in turn allows air to flow over the wings and generate lift.
- idx 14: Without sufficient thrust, there wouldn't be enough airflow to create the pressure difference needed for lift.
- idx 15: Once lift is greater than the weight of the airplane, it can take off and fly.
- idx 16: Pilots constantly adjust the engine power and the position of control surfaces like ailerons and elevators to manage lift, drag, thrust, and weight, ensuring a stable and controlled flight.
- idx 17: Understanding these fundamental **physics** principles is paramount for **engineering** safer and more efficient **airplanes**.
- idx 18: It’s a continuous process of innovation, figuring out how to maximize **lift** and minimize **drag** for everything from small private jets to massive commercial airliners.

## 0b39ed43-18c6-4c9c-977b-c2fc4837415f — Green Cities, Happy People, Smart Investment

Passage (for context, do not translate as a block unless the arm says so):

Big trees and green parks are good for cities. They make the city look nice. People like to walk in the green spaces. This makes people happy. When cities have more green, people want to live there. More people living there means houses cost more money. This is good for **real estate**. Growing food up high on buildings is a new idea. These are called vertical farms. They help people get fresh food. This is good for **food security**. It means everyone can get food. Vertical farms use less water. They also help the air stay clean. This is good for **sustainability**. Putting money into green spaces and farms is a smart **investment**. It helps the city grow. Good **urban planning** puts trees and farms in the right places. This makes the city a better place for everyone.

Sentences:

- idx 0: Big trees and green parks are good for cities.
- idx 1: They make the city look nice.
- idx 2: People like to walk in the green spaces.
- idx 3: This makes people happy.
- idx 4: When cities have more green, people want to live there.
- idx 5: More people living there means houses cost more money.
- idx 6: This is good for **real estate**.
- idx 7: Growing food up high on buildings is a new idea.
- idx 8: These are called vertical farms.
- idx 9: They help people get fresh food.
- idx 10: This is good for **food security**.
- idx 11: It means everyone can get food.
- idx 12: Vertical farms use less water.
- idx 13: They also help the air stay clean.
- idx 14: This is good for **sustainability**.
- idx 15: Putting money into green spaces and farms is a smart **investment**.
- idx 16: It helps the city grow.
- idx 17: Good **urban planning** puts trees and farms in the right places.
- idx 18: This makes the city a better place for everyone.

## 97330b8b-31d2-42c3-bdb4-e33b13571639 — Nations Combatting Single-Use Plastics: Diverse Policies for a Greener Future

Passage (for context, do not translate as a block unless the arm says so):

Many nations are now focusing on tackling plastic pollution. They are introducing new legislation to limit the use of single-use plastics. This environmental policy is a response to growing concerns about waste. These materials, which we use only once, then throw away, often end up in oceans and landfills. Some countries have implemented outright bans on certain items, such as plastic bags and straws. Other nations have chosen a phased approach, gradually reducing the availability of these products. For instance, a country might first impose a fee on plastic bags, encouraging people to bring their own reusable ones. If this measure proves effective, they might then consider a complete ban. This strategy allows consumers and businesses time to adjust. The goal of such regulation is to curb the massive amount of plastic waste generated daily. This waste harms wildlife and can take hundreds of years to decompose. By making single-use plastics less accessible, governments hope to encourage people to adopt more sustainable habits. This includes using reusable containers, water bottles, and shopping bags. These changes are part of broader global trends. Many international organizations are advocating for stronger environmental policies. They highlight how effective national legislation can contribute to a healthier planet. While some argue that these regulations can be inconvenient or costly, many see the long-term benefits. Reducing plastic pollution is crucial for preserving ecosystems and protecting human health. The debate continues about the best ways to implement these policies, but the commitment to addressing plastic pollution is gaining momentum worldwide. It is becoming clear that proactive environmental policy is essential.

Sentences:

- idx 0: Many nations are now focusing on tackling plastic pollution.
- idx 1: They are introducing new legislation to limit the use of single-use plastics.
- idx 2: This environmental policy is a response to growing concerns about waste.
- idx 3: These materials, which we use only once, then throw away, often end up in oceans and landfills.
- idx 4: Some countries have implemented outright bans on certain items, such as plastic bags and straws.
- idx 5: Other nations have chosen a phased approach, gradually reducing the availability of these products.
- idx 6: For instance, a country might first impose a fee on plastic bags, encouraging people to bring their own reusable ones.
- idx 7: If this measure proves effective, they might then consider a complete ban.
- idx 8: This strategy allows consumers and businesses time to adjust.
- idx 9: The goal of such regulation is to curb the massive amount of plastic waste generated daily.
- idx 10: This waste harms wildlife and can take hundreds of years to decompose.
- idx 11: By making single-use plastics less accessible, governments hope to encourage people to adopt more sustainable habits.
- idx 12: This includes using reusable containers, water bottles, and shopping bags.
- idx 13: These changes are part of broader global trends.
- idx 14: Many international organizations are advocating for stronger environmental policies.
- idx 15: They highlight how effective national legislation can contribute to a healthier planet.
- idx 16: While some argue that these regulations can be inconvenient or costly, many see the long-term benefits.
- idx 17: Reducing plastic pollution is crucial for preserving ecosystems and protecting human health.
- idx 18: The debate continues about the best ways to implement these policies, but the commitment to addressing plastic pollution is gaining momentum worldwide.
- idx 19: It is becoming clear that proactive environmental policy is essential.
