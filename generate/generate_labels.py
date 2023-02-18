import json
import os

SCENES_FOLDER = 'generate/Out/scenes'
LABELS_FOLDER = 'generate/Out/'

def get_video(scene):
    """Get the image file name from the scene."""
    s = json.load(open(f'generate/Out/scenes/{scene}'))
    return s['image_filename']

def get_moves(scene):
    """ Get the moves for a scene.
    Returns a list of tuples of the form (object_name, action, target, start_frame, end_frame)
    """
    s = json.load(open(f'generate/Out/scenes/{scene}'))
    moves = s['movements']
    cleaned = []
    for object_name in moves:
        for ac in moves[object_name]:
            if ac[0] == '_no_op':
                continue
            cleaned.append([object_name]+ac)
    # Sort by start frame (3rd element of tuple)
    cleaned.sort(key=lambda x: x[3])
    return cleaned

def who_contains_who(moves,time_point):
    """
    Returns a dictionary where the key is the object that contains
    the other object.
    """
    contains = {}
    # Initialize all objects to not contain anything
    for i in range(len(moves)):
        contains[moves[i][0]] = None
    for i in range(len(moves)):
        if moves[i][3] > time_point:
            break
        if moves[i][1] == '_contain':
            contains[moves[i][0]] = moves[i][2]
        elif moves[i][1] == '_pick_place':
            contains[moves[i][0]] = None
    return contains

def detect_overlap(moves):
    """
    Detects if there is any overlap in the moves and which one is the main and which one is the sub.
    """
    for i in range(len(moves)):
        for j in range(i+1, len(moves)):
            if moves[i][3] == moves[j][3]:
                contains = who_contains_who(moves, moves[i][3])
                if contains[moves[i][0]] == moves[j][0]:
                    return True, i, j
                if contains[moves[j][0]] == moves[i][0]:
                    return True, j, i
    return False, None, None

def get_objects(scene):
    s = json.load(open(f'generate/Out/scenes/{scene}'))
    objects =  s['objects']
    cleaned = {} # key is object name, value is color, material, shape
    for obj in objects:
        cleaned[obj['instance']] = ",%s,%s,%s,"%(obj['color'], obj["material"], obj['shape'])
    return cleaned

def instance_to_label(scene, instance):
    objects = get_objects(scene)
    return objects[instance]

def get_label(scene):
    moves = get_moves(scene)
    is_overlapping, main, sub = detect_overlap(moves)
    # For each move: Action, Color, Material, Shape
    if not is_overlapping:
        label = ""
        for i in range(len(moves)):
            label += moves[i][1]
            label += instance_to_label(scene, moves[i][0])
        return label[:-1] # remove last comma

    else:
        if sub < main:
            # switch elements in list
            moves[main], moves[sub] = moves[sub], moves[main]
            main, sub = sub, main
        label = ""
        for i in range(len(moves)):
            if i == sub:
                label += 'containing'
            else:
                label+= moves[i][1]
            label+= instance_to_label(scene, moves[i][0])
        return label[:-1] # remove last comma

def get_all_labels():
    scenes = os.listdir(SCENES_FOLDER)
    scenes.sort()
    
    labels = []
    for i in range(len(scenes)):
        label = get_label(scenes[i])
        video = get_video(scenes[i])
        print(scenes[i], video, label)
        labels.append((video,label))
    return labels

def split_train_val_test(labels):
    """First split 20% of the data into test
    Then split 20% of the remaining data into validation
    The rest is training.

    The test set has all occurences of:
    - gray cube
    - metal sphere
    - slide red
    - rotate metal
    - blue metal
    - pick_place gray rubber cone
    """
    def is_test_label(label):
        shape_color = label[1] == 'gray' and label[3] == 'cube'
        shape_material = label[2] == 'metal' and label[3] == 'sphere'
        action_color = label[0] == '_slide' and label[1] == 'red'
        action_material = label[0] == '_rotate' and label[2] == 'metal'
        color_material = label[1] == 'blue' and label[2] == 'metal'
        action_color_material_shape = label==['_pick_place', 'gray', 'rubber', 'cone']
        return shape_color or shape_material or action_color or action_material or color_material# or action_color_material_shape

    test = []
    val = []
    train = []
    for i in range(len(labels)):
        label = labels[i][1].split(',') # every 4 elements is a move

        assert len(label) % 4 == 0
        for i in range(0, len(label), 4):
            if is_test_label(label[i:i+4]):
                test.append(labels[i])
                break
        else:
            train.append(labels[i])

    # Split train into val and train
    for i in range(len(train)):
        if i % 5 == 0:
            val.append(train[i])
        else:
            train.append(train[i])
    return train, val, test

def format_prettier(labels):
    pretty = ""
    for i in range(len(labels)):
        pretty += labels[i][0] + ':' + labels[i][1] + '\n'
    return pretty

if __name__ == '__main__':
    labels = get_all_labels()
    train, val, test = split_train_val_test(labels)
    sum_ = len(train) + len(val) + len(test)
    print(F'Train: {len(train)}/{sum_} = {len(train)/sum_}')
    print(F'Val: {len(val)}/{sum_} = {len(val)/sum_}')
    print(F'Test: {len(test)}/{sum_} = {len(test)/sum_}')
    with open(f'{LABELS_FOLDER}train.txt', 'w') as f:
        f.write(format_prettier(train))
    with open(f'{LABELS_FOLDER}val.txt', 'w') as f:
        f.write(format_prettier(val))
    with open(f'{LABELS_FOLDER}test.txt', 'w') as f:
        f.write(format_prettier(test))
    print('Done')
    

