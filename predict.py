import argparse
from utils.dect_lang import create_cslang_list
from utils.helpers import read_lines, normalize, retry
from gector.gec_model import GecBERTModel
from googletrans import Translator
import httpcore


def find_spans(cs_list):
    spans = []
    start = None

    for i in range(len(cs_list)):
        if cs_list[i]:
            if start is None:
                start = i
        else:
            if start is not None:
                spans.append([start, i])
                start = None

    if start is not None:
        spans.append([start, len(cs_list)])

    return spans

def predict_for_file(input_file, output_file, model, batch_size=32, to_normalize=False):
    test_data = read_lines(input_file)
    predictions = []
    final_cs_list = []
    final_ori_list = []
    cnt_corrections = 0
    batch = []
    batch_list = []
    batch_list_ori = []
    if args.pre_translate:
        translator = Translator()
        new_test_data = []
        new_ori_test_data = []
        new_test_cs_list = []
        for sentence in test_data:
            test_cs_words = sentence.replace("\u3000", " ").split(" ")
            test_cs_list = [not words for words in create_cslang_list(test_cs_words)]
            test_cs_spans = find_spans(test_cs_list)
            phrases_to_translate = [" ".join(test_cs_words[id[0]:id[1]]) for id in test_cs_spans]
            # translate the cs_phrases
            try:
                translation = retry(translator.translate(phrases_to_translate, dest="EN"), ex_type=httpcore._exceptions.ReadTimeout, limit=10, wait_ms=100, wait_increase_ratio=10, logger=None)
            except httpcore._exceptions.ReadTimeout:
                print ("Timeout Error - Phrases: {}".format(phrases_to_translate))
            translation = [trans.text for i, trans in enumerate(translation)]

            # replace the selected phrase with its translation
            new_cs_words = []
            new_cs_list = []
            ori_test_data = []
            for i in range(len(test_cs_words)):
                within_span = False
                for j, span in enumerate(test_cs_spans):
                    if i == span[0]:
                        new_cs_words.append(translation[j])
                        new_cs_list.append(True)
                        ori_test_data.append(" ".join(test_cs_words[span[0]:span[1]]))
                        within_span = True
                    elif i > span[0] and i < span[1]:
                        within_span = True
                if not within_span:
                    new_cs_words.append(test_cs_words[i])
                    ori_test_data.append(test_cs_words[i])
                    new_cs_list.append(False)
            new_test_data.append(new_cs_words)
            new_test_cs_list.append(new_cs_list)
            new_ori_test_data.append(ori_test_data)
        test_data = new_test_data
        cs_list = new_test_cs_list
        test_data_ori = new_ori_test_data
    else:
        test_data = [sent.split() for sent in test_data]

    for j, sent in enumerate(test_data):
        batch.append(sent)
        if args.pre_translate:
            batch_list.append(cs_list[j])
            batch_list_ori.append(test_data_ori[j])
        else:
            batch_list.append([False]*len(sent))
            batch_list_ori.append(test_data[j])
        if len(batch) == batch_size:
            preds, new_cs_list, new_ori_data, cnt = model.handle_batch(batch, batch_list, batch_list_ori)
            predictions.extend(preds)
            final_cs_list.extend(new_cs_list)
            final_ori_list.extend(new_ori_data)
            cnt_corrections += cnt
            batch = []
            batch_list = []
            batch_list_ori = []
    if batch:
        preds, new_cs_list, new_ori_data, cnt = model.handle_batch(batch, batch_list, batch_list_ori)
        predictions.extend(preds)
        final_cs_list.extend(new_cs_list)
        final_ori_list.extend(new_ori_data)
        cnt_corrections += cnt

    if args.pre_translate:
        # Replace translated portions
        for i, sentence in enumerate(predictions):
            for j in range(len(sentence)):
                if final_cs_list[i][j]:
                    predictions[i][j] = final_ori_list[i][j]

    result_lines = [" ".join(x) for x in predictions]
    if to_normalize:
        result_lines = [normalize(line) for line in result_lines]

    with open(output_file, 'w') as f:
        f.write("\n".join(result_lines) + '\n')
    return cnt_corrections


def main(args):
    # get all paths
    model = GecBERTModel(vocab_path=args.vocab_path,
                         model_paths=args.model_path,
                         max_len=args.max_len, min_len=args.min_len,
                         iterations=args.iteration_count,
                         min_error_probability=args.min_error_probability,
                         lowercase_tokens=args.lowercase_tokens,
                         model_name=args.transformer_model,
                         special_tokens_fix=args.special_tokens_fix,
                         log=False,
                         confidence=args.additional_confidence,
                         del_confidence=args.additional_del_confidence,
                         is_ensemble=args.is_ensemble,
                         weigths=args.weights)

    cnt_corrections = predict_for_file(args.input_file, args.output_file, model,
                                       batch_size=args.batch_size, 
                                       to_normalize=args.normalize)
    # evaluate with m2 or ERRANT
    print(f"Produced overall corrections: {cnt_corrections}")


if __name__ == '__main__':
    # read parameters
    parser = argparse.ArgumentParser()
    parser.add_argument('--model_path',
                        help='Path to the model file.', nargs='+',
                        required=True)
    parser.add_argument('--vocab_path',
                        help='Path to the model file.',
                        default='data/output_vocabulary'  # to use pretrained models
                        )
    parser.add_argument('--input_file',
                        help='Path to the evalset file',
                        required=True)
    parser.add_argument('--output_file',
                        help='Path to the output file',
                        required=True)
    parser.add_argument('--max_len',
                        type=int,
                        help='The max sentence length'
                             '(all longer will be truncated)',
                        default=50)
    parser.add_argument('--min_len',
                        type=int,
                        help='The minimum sentence length'
                             '(all longer will be returned w/o changes)',
                        default=3)
    parser.add_argument('--batch_size',
                        type=int,
                        help='The size of hidden unit cell.',
                        default=128)
    parser.add_argument('--lowercase_tokens',
                        type=int,
                        help='Whether to lowercase tokens.',
                        default=0)
    parser.add_argument('--transformer_model',
                        choices=['bert', 'distilbert', 'gpt2', 'roberta', 'transformerxl', 'xlnet', 'albert',
                                 'bert-large', 'roberta-large', 'xlnet-large', 'xlm-roberta', 'xlm-roberta-large'],
                        help='Name of the transformer model.',
                        default='roberta')
    parser.add_argument('--iteration_count',
                        type=int,
                        help='The number of iterations of the model.',
                        default=5)
    parser.add_argument('--additional_confidence',
                        type=float,
                        help='How many probability to add to $KEEP token.',
                        default=0)
    parser.add_argument('--additional_del_confidence',
                        type=float,
                        help='How many probability to add to $DELETE token.',
                        default=0)
    parser.add_argument('--min_error_probability',
                        type=float,
                        help='Minimum probability for each action to apply. '
                             'Also, minimum error probability, as described in the paper.',
                        default=0.0)
    parser.add_argument('--special_tokens_fix',
                        type=int,
                        help='Whether to fix problem with [CLS], [SEP] tokens tokenization. '
                             'For reproducing reported results it should be 0 for BERT/XLNet and 1 for RoBERTa.',
                        default=1)
    parser.add_argument('--is_ensemble',
                        type=int,
                        help='Whether to do ensembling.',
                        default=0)
    parser.add_argument('--weights',
                        help='Used to calculate weighted average', nargs='+',
                        default=None)
    parser.add_argument('--normalize',
                        help='Use for text simplification.',
                        action='store_true')
    parser.add_argument('--pre_translate',
                        type=int,
                        help='Whether to translate the code-switched sentences to English before evaluating on model.',
                        default=0)
    args = parser.parse_args()
    main(args)
