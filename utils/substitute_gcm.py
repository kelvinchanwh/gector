import sys
import benepar
import random
from googletrans import Translator
from tqdm import tqdm
import time
import httpcore
import multiprocessing

def retry(func, ex_type=Exception, limit=0, wait_ms=100, wait_increase_ratio=2, logger=None):
    """
    Retry a function invocation until no exception occurs
    :param func: function to invoke
    :param ex_type: retry only if exception is subclass of this type
    :param limit: maximum number of invocation attempts
    :param wait_ms: initial wait time after each attempt in milliseconds.
    :param wait_increase_ratio: increase wait period by multiplying this value after each attempt.
    :param logger: if not None, retry attempts will be logged to this logging.logger
    :return: result of first successful invocation
    :raises: last invocation exception if attempts exhausted or exception is not an instance of ex_type
    """
    attempt = 1
    while True:
        try:
            return func
        except Exception as ex:
            if not isinstance(ex, ex_type):
                raise ex
            if 0 < limit <= attempt:
                if logger:
                    logger.warning("no more attempts")
                raise ex

            if logger:
                logger.error("failed execution attempt #%d", attempt, exc_info=ex)

            attempt += 1
            if logger:
                logger.info("waiting %d ms before attempt #%d", wait_ms, attempt)
            time.sleep(wait_ms / 1000)
            wait_ms *= wait_increase_ratio


def apply_edit_to_cs(cs_words, cs_list, m2_edits):
	"""
	
	"""
	sid = eid = 0
	prev_sid = prev_eid = -1
	pos = 0
	corrected = list()
	corrected = ['<S>'] + cs_words[:]
	for i in range(len(m2_edits)):
		edit = m2_edits[i]
		sid = int(edit[0][0]) + 1
		eid = int(edit[0][1]) + 1
		error_type = edit[1]
		if error_type == "Um":
			continue
		if sum(cs_list[sid-1:eid]) > 0:
			continue
		for idx in range(sid, eid):
			corrected[idx] = ""
		if sid == eid:
			if sid == 0: continue	# Originally index was -1, indicating no op
			if sid != prev_sid or eid != prev_eid:
				pos = len(corrected[sid-1].split())
			cur_words = corrected[sid-1].split()
			cur_words.insert(pos, edit[2])
			pos += len(edit[2].split())
			corrected[sid-1] = " ".join(cur_words)
		else:
			corrected[sid] = edit[2]
			pos = 0
		prev_sid = sid
		prev_eid = eid
	else:
		target_sentence = [word for word in corrected if word != ""]
		if target_sentence[0].strip() != "<S>":
			if target_sentence[0].startswith("<S> "):
				target_sentence[0] = target_sentence[0][4:]
				return target_sentence
			else:
				print ('Sentence does not start with <S> (' + str(target_sentence) + ')')

		target_sentence = target_sentence[1:]
		return target_sentence

def parse_m2(input_m2_path):
	m2_dict = dict()
	with open(input_m2_path) as input_m2:
		# English Sentence
		for line in input_m2:
			line = line.strip()
			if line.startswith('S'):
				line = line[2:]
				S = "".join(line.split(" "))
				m2_dict[S] = {"corr": line.split(" ")  , "edits":[]}
			elif line.startswith('A'):
				line = line[2:]
				info = line.split("|||")
				info[0] = [int(i) for i in info[0].split(" ")]
				m2_dict[S]["edits"].append(info)
	return m2_dict


def sub_cs(m2, parser, translator, src_lang="en", tgt_lang="zh-tw", select = 'random', verbose = False):
	# parse the sentence using Benepar
	sentence = m2["corr"]
	tree = parser.parse(sentence)

	for idx, _ in enumerate(tree.leaves()):
		tree_location = tree.leaf_treeposition(idx)
		non_terminal = tree[tree_location[:-1]]
		non_terminal[0] = non_terminal[0] + "|:::|" + str(idx)

	# create a list of all phrases in the sentence
	phrases = []
	for subtree in tree.subtrees():
		if subtree.label() in ['NP', 'VP', 'PP', 'ADJP', 'ADVP']:
			leaves = subtree.leaves()
			leaf_positions = [int(leaf.split("|:::|")[1]) for leaf in leaves]
			phrase = [leaf.split("|:::|")[0] for leaf in leaves]
			leaf_start, leaf_end = min(leaf_positions), max(leaf_positions)+1
			if leaf_start <= 0 and leaf_end >= len(sentence):
				# Ignore translation of entire sentence
				pass
			else:
				phrases.append((' '.join(phrase), leaf_start, leaf_end))

	if len(phrases)>0:
		if select == 'random':
			# randomly select a phrase to translate
			phrase_to_translate, start, end = random.choice(phrases)
		
		sentence = [leaf.split("|:::|")[0] for leaf in tree.leaves()]

		# translate the selected phrase
		try:
			translation = retry(translator.translate(phrase_to_translate, src=src_lang, dest=tgt_lang), ex_type=httpcore._exceptions.ReadTimeout, limit=10, wait_ms=100, wait_increase_ratio=2, logger=None)
		except httpcore._exceptions.ReadTimeout:
			print ("Timeout Error - Sentence: {}".format(" ".join(sentence)))
			# Return original sentence
			return (sentence, [False]*len(sentence), -1, -1)
		translation = translation.text
		# replace the selected phrase with its translation
		new_sentence = sentence[:start] + [translation] + ["<CS_FILL>"]*(end-start-1) + sentence[end:]
		cs_list = [False] * start + [True] * (end-start) + [False] * (len(sentence)-end)

		if verbose:
			# print the original and translated sentences, and the span
			print(f"Original sentence: {sentence}")
			print(f"Translated sentence: {new_sentence}")
			print(f"Translated span: ({start}, {end})")

		return (new_sentence, cs_list, start, end)
	else:
		return (sentence, [False]*len(sentence), -1, -1)
	
def main(in_m2, parser, translator):
	cs_words, cs_list, start, end = sub_cs(in_m2, parser, translator)
	
	if max([m2_edit[0][1] for m2_edit in in_m2["edits"]]) <= len(cs_list):
		incorr = apply_edit_to_cs(cs_words, cs_list, in_m2["edits"])

		corr = [i for i in cs_words if i != "<CS_FILL>"]
		incorr = [i for i in incorr if i != "<CS_FILL>"]

		corr = " ".join(corr)
		incorr = " ".join(incorr)

		output_cs_incorr.write(incorr + '\n')
		output_cs_corr.write(corr + '\n')
	else:
		print ("Sentence is shorter than m2 edit")

if __name__ == "__main__":
	if len(sys.argv) != 4:
		print("[USAGE] %s input_inv_m2_file output_cs_incorr output_cs_corr" % sys.argv[0])
		sys.exit()

	# define a sentence to parse and translate
	input_path = sys.argv[1]
	output_cs_incorr_path = sys.argv[2]
	output_cs_corr_path = sys.argv[3]

	# download and load the Benepar model
	# benepar.download('benepar_en3')
	parser = benepar.Parser('benepar_en3')

	# create a translator object
	translator = Translator()

	with open(output_cs_incorr_path, "w+") as output_cs_incorr, open(output_cs_corr_path, "w+") as output_cs_corr:
		in_m2  = parse_m2(input_path)
		for sentence in tqdm(in_m2.values()):
			main(sentence, parser, translator)

