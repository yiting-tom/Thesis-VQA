#%%
"""
This file defines 2 preprocessing functions for VQA-E dataset
for questions and answers.
"""
import json
import numpy as np
from typing import Counter, Dict, List
from pathlib import Path
from tqdm import tqdm
from util import utils
from configs.logger import l
from configs import paths, consts


def process_vqa_questions(
    dataset_type: str,
    vocab_dict: Dict[str, int],
    q_len: int,
    vqa_dir: str,
    save_path: str,
) -> None:
    """process_vqa_questions

    Args:
        dataset_type (str): The dataset type
        vocab_dict (Dict[str, int]): The vocabulary dictionary
        q_len (int): The maximum length of the question
        vqa_dir (str): The directory of the VQA dataset
        save_path (str): The json file to save the processed data
    """
    l.info(f"Preprocessing VQA {dataset_type} question data")
    with open(f"{vqa_dir}/v2_OpenEnded_mscoco_{dataset_type}2014_questions.json") as f:
        q_json = json.load(f)["questions"]

    save_path = Path(save_path) / "vqa"
    save_path.mkdir(parents=True, exist_ok=True)
    q_data = []
    current_chunk_index = 0
    chunk_size = (
        consts.COCO_TRAIN2014_QA_CHUNK_SIZE
        if dataset_type == "train"
        else consts.COCO_VAL2014_QA_CHUNK_SIZE
    )
    # Iterate over the questions
    # q is a dict like this: {
    #     'image_id': 524291,
    #     'question': "What is in the person's hand?"
    #     'question_id': 524291000,
    # }
    for i, q in tqdm(
        enumerate(q_json),
        desc=f"VQA {dataset_type} question",
        total=len(q_json),
    ):
        image_id: int = q["image_id"]
        filename = (
            f"{dataset_type}2014/COCO_{dataset_type}2014_{str(image_id).zfill(12)}.npz"
        )
        # read the image feature
        image_data = np.load(paths.d_COCO_FEATURE / filename)["x"]
        # read the image relationship graph
        graph_data = np.load(paths.d_COCO_GRAPH / filename)["graph"]
        # get the question string
        q_string = q["question"]

        _, ids = utils.get_tokens_and_ids(
            sentence=q_string,
            vocab_dict=vocab_dict,
        )
        ids, _ = utils.padding_ids(
            ids=ids,
            max_len=q_len,
            vocab_dict=vocab_dict,
        )
        q_data.append(
            {
                "image_feature": image_data,
                "image_graph": graph_data,
                "q_token_ids": ids,
            }
        )

        if (i + 1) % chunk_size == 0:
            # Save the processed data
            result_save_path = (
                save_path / f"{dataset_type}2014_questions-chunk_{current_chunk_index}"
            )
            l.info(
                f"Saving preprocessed VQA {dataset_type} question data to {result_save_path}"
            )
            np.save(result_save_path, q_data)
            current_chunk_index += 1
            del q_data
            q_data = []

    if (i + 1) % chunk_size != 0:
        # Save the processed data
        result_save_path = (
            save_path / f"{dataset_type}2014_questions-chunk_{current_chunk_index}"
        )
        l.info(
            f"Saving preprocessed VQA {dataset_type} question data to {result_save_path}"
        )
        np.save(result_save_path, q_data)


def process_vqa_answers(
    dataset_type: str,
    vocab_dict: Dict[str, int],
    ans_dict: Dict[str, int],
    vqa_dir: str,
    save_path: str,
) -> None:
    """process_vqa_answers

    Args:
        dataset_type (str): The dataset type
        vocab_dict (Dict[str, int]): The vocabulary dictionary
        ans_dict (Dict[str, int]): The answer dictionary
        vqa_dir (str): The directory of the VQA dataset
        save_path (str): The json file to save the processed data
    """
    l.info(f"Preprocessing VQA {dataset_type} answer data")
    with open(f"{vqa_dir}/v2_mscoco_{dataset_type}2014_annotations.json") as f:
        a_json = json.load(f)["annotations"]

    a_data = []
    answer_types = {"yes/no": [], "number": [], "other": []}
    # a is a dict like this: {
    #    'question_type': 'what is this',
    #    'multiple_choice_answer': 'net',
    #    'answers': [
    #        {'answer': 'net', 'answer_confidence': 'maybe', 'answer_id': 1},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 2},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 3},
    #        {'answer': 'netting', 'answer_confidence': 'yes', 'answer_id': 4},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 5},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 6},
    #        {'answer': 'mesh', 'answer_confidence': 'maybe', 'answer_id': 7},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 8},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 9},
    #        {'answer': 'net', 'answer_confidence': 'yes', 'answer_id': 10}
    #     ],
    #    'image_id': 458752,
    #    'answer_type': 'other',
    #    'question_id': 458752000,
    # }
    for idx, row in tqdm(
        enumerate(a_json),
        desc=f"VQA {dataset_type} answer",
        total=len(a_json),
    ):
        answers: List[str] = []

        # get all answers from answer dictionary
        for answer_dict in row["answers"]:
            answers.append(answer_dict["answer"])

        # count the number of each answer
        cnt = Counter(answers)

        # filter out the answer which appears in the answer dictionary
        filtered_answers = dict(
            filter(
                lambda x: x[0] in ans_dict,
                cnt.items(),
            )
        )

        # encode the tokens
        ans_cnt_dict = dict(
            zip(
                utils.tokens_to_ids(
                    token_list=filtered_answers.keys(),
                    vocab_dict=vocab_dict,
                ),
                filtered_answers.values(),
            )
        )

        # record the answer counter dictionary
        a_data.append(ans_cnt_dict)

        # record the answer counter dictionary
        answer_types[row["answer_type"]].append(idx)

    result_save_path: Path = Path(f"{save_path}/vqa/{dataset_type}2014_answers")
    # Ensure the directory exists
    result_save_path.parent.mkdir(parents=True, exist_ok=True)
    # Save the processed data
    l.info(f"Saving preprocessed VQA {dataset_type} answer data to {result_save_path}")
    np.save(result_save_path, a_data)

    # Save the answer type
    if dataset_type == "val":
        answer_type_file: Path = Path(f"{save_path}/vqa_answer_types")
        l.info(
            f"Pickling preprocessed VQA {dataset_type} answer type to {answer_type_file}"
        )
        np.save(answer_type_file, answer_types)
