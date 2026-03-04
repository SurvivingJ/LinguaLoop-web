#!/usr/bin/env python3
"""Quick verification script to test the distribution logic"""

# Simulate the config structure
TOPIC_DIFFICULTY_CONFIGS = {
    'english': {
        'beginner': [('Topic', i) for i in [1,1,2,2,3,3,1,2,3]],
        'intermediate': [('Topic', i) for i in [4,5,4,5,6,6,4,5,6]],
        'advanced': [('Topic', i) for i in [7,8,7,9,8,7,8,9,9]]
    },
    'chinese': {
        'beginner': [('Topic', i) for i in [1,1,2,2,3,1,2,3,2]],
        'intermediate': [('Topic', i) for i in [4,5,4,5,6,6,4,5,6]],
        'advanced': [('Topic', i) for i in [7,8,7,9,8,7,8,9,9]]
    },
    'japanese': {
        'beginner': [('Topic', i) for i in [1,1,2,2,3,1,2,3,2]],
        'intermediate': [('Topic', i) for i in [4,5,4,5,6,6,4,5,6]],
        'advanced': [('Topic', i) for i in [7,8,7,9,8,7,8,9,9]]
    }
}

# Test the generation logic
configs = []
TARGETS = {'english': 83, 'chinese': 83, 'japanese': 84}

for language, target in TARGETS.items():
    per_level = target // 3
    remainder = target % 3

    level_targets = {
        'beginner': per_level + (1 if remainder > 0 else 0),
        'intermediate': per_level + (1 if remainder > 1 else 0),
        'advanced': per_level
    }

    for level in ['beginner', 'intermediate', 'advanced']:
        topic_difficulty_pairs = TOPIC_DIFFICULTY_CONFIGS[language][level]
        count = 0

        while count < level_targets[level]:
            pair = topic_difficulty_pairs[count % len(topic_difficulty_pairs)]
            configs.append({
                'language': language,
                'difficulty': pair[1],
                'topic': pair[0]
            })
            count += 1

# Verify distribution
print(f'Total: {len(configs)}')
print()

for lang in ['english', 'chinese', 'japanese']:
    lang_configs = [c for c in configs if c['language'] == lang]
    print(f'{lang.title()}: {len(lang_configs)}')
    for level, range_ in [('Beginner', [1,2,3]), ('Intermediate', [4,5,6]), ('Advanced', [7,8,9])]:
        count = len([c for c in lang_configs if c['difficulty'] in range_])
        print(f'  {level} (D{range_[0]}-{range_[-1]}): {count}')
    print()

# Overall difficulty distribution
print('Overall Difficulty Distribution:')
beginner = len([c for c in configs if c['difficulty'] in [1,2,3]])
intermediate = len([c for c in configs if c['difficulty'] in [4,5,6]])
advanced = len([c for c in configs if c['difficulty'] in [7,8,9]])
print(f'  Beginner (D1-3): {beginner}')
print(f'  Intermediate (D4-6): {intermediate}')
print(f'  Advanced (D7-9): {advanced}')
print()
print('✅ Distribution verified!' if len(configs) == 250 else '❌ Distribution incorrect!')
