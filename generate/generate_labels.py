import json
import os

SCENES_FOLDER = 'generate/Out/scenes'
LABELS_FOLDER = 'generate/Out/'

DICTIONARY = ['EOS', '_containing', '_contain', '_pick_place', '_rotate', '_slide',
              'metal', 'rubber',
              'yellow', 'cyan', 'gold', 'brown', 'red', 'gray', 'purple', 'blue', 'green',
              'sphere', 'cube', 'cylinder', 'cone', 'spl']

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
    """Get the objects for a scene."""
    s = json.load(open(f'generate/Out/scenes/{scene}'))
    objects =  s['objects']
    cleaned = {} # key is object name, value is color, material, shape
    for obj in objects:
        cleaned[obj['instance']] = (obj['color'], obj["material"], obj['shape'])
    return cleaned

def instance_to_label(scene, instance):
    """Converts the instance to the object's label.
    
    Retrieves the object from the scene given the instance name.
    Returns a list of the form [color, material, shape]
    """
    objects = get_objects(scene)
    return objects[instance]

def get_dictionary_label(label):
    """Converts the label to the index in the dictionary."""
    dictionary_label = []
    for i in range(len(label)):
        dictionary_label.append(DICTIONARY.index(label[i]))
    return dictionary_label

def get_label(scene):
    """Get the label for a scene."""
    moves = get_moves(scene)
    is_overlapping, main, sub = detect_overlap(moves)
    # For each move: Action, Color, Material, Shape
    if not is_overlapping:
        label = []
        for i in range(len(moves)):
            label.append(moves[i][1])
            label.extend(instance_to_label(scene, moves[i][0]))
    else:
        if sub < main:
            # switch elements in list
            moves[main], moves[sub] = moves[sub], moves[main]
            main, sub = sub, main
        label = []
        for i in range(len(moves)):
            if i == sub:
                label.append('_containing')
            else:
                label.append(moves[i][1])
            label.extend(instance_to_label(scene, moves[i][0]))
        
    dict_label = get_dictionary_label(label)
    dict_label.append(DICTIONARY.index('EOS')) # always end with EOS
    return dict_label

def get_all_labels():
    """Get all labels for all scenes."""
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
    - blue rubber
    """
    def is_test_label(label):
        shape_color = label[1] == DICTIONARY.index('gray') and label[3] == DICTIONARY.index('cube')
        shape_material = label[2] == DICTIONARY.index('metal') and label[3] == DICTIONARY.index('sphere')
        action_color = label[0] == DICTIONARY.index('_slide') and label[1] == DICTIONARY.index('red')
        action_material = label[0] == DICTIONARY.index('_rotate') and label[2] == DICTIONARY.index('metal')
        color_material = label[1] == DICTIONARY.index('blue') and label[2] == DICTIONARY.index('rubber')
        return shape_color or shape_material or action_color or action_material or color_material

    test = []
    not_test = []
    for i in range(len(labels)):
        label = labels[i][1] # 0 is video, 1 is label

        assert len(label) % 4 == 1 # 4 elements per move + 1 for EOS
        is_test = False
        for j in range(0, len(label) - 1, 4):
            if is_test_label(label[j:j+4]):
                is_test = True
                break

        if is_test:
            print('test', labels[i])
            test.append(labels[i])
        else:
            not_test.append(labels[i])

    # Split test into val and test
    test_val = []
    test_ = []
    for i in range(len(test)):
        if i % 4 == 0:
            test_val.append(test[i])
        else:
            test_.append(test[i])

    # Split train into val and train
    val = []
    train = []
    for i in range(len(not_test)):
        if i % 3 == 0:
            val.append(not_test[i])
        else:
            train.append(not_test[i])
    return train, val, test_, test_val

def format_prettier(labels):
    pretty = ""
    for i in range(len(labels)):
        pretty += labels[i][0] + ':' # video
        pretty += str(labels[i][1]).replace(' ','')[1:-1] + '\n' # label but without the brackets and spaces
        
    return pretty

if __name__ == '__main__':
    labels = get_all_labels()
    train, val, test_, test_val = split_train_val_test(labels)
    sum_ = len(train) + len(val) + len(test_) + len(test_val)
    print(F'Train: {len(train)}/{sum_} = {len(train)/sum_}')
    print(F'Val: {len(val)}/{sum_} = {len(val)/sum_}')
    print(F'Test: {len(test_)}/{sum_} = {len(test_)/sum_}')
    print(F'Test val: {len(test_val)}/{sum_} = {len(test_val)/sum_}')
    with open(f'{LABELS_FOLDER}train.txt', 'w') as f:
        f.write(format_prettier(train))
    with open(f'{LABELS_FOLDER}val.txt', 'w') as f:
        f.write(format_prettier(val))
    with open(f'{LABELS_FOLDER}test.txt', 'w') as f:
        f.write(format_prettier(test_))
    with open(f'{LABELS_FOLDER}test_val.txt', 'w') as f:
        f.write(format_prettier(test_val))
    print('Done')
    

