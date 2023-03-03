import sys
import benepar
import random
from googletrans import Translator
from tqdm import tqdm
import time
import httpcore
import multiprocessing
import platform

def divide_chunks(l, n):
    # looping till length l
    for i in range(0, len(l), n):
        yield l[i:i + n]
	

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

def select_least_intersect(cs_intervals, edits):
    def interval_intersection(a, b):
        return max(0, min(a[1], b[1]) - max(a[0], b[0]))
    
    def total_intersection(interval, intervals):
        return sum(interval_intersection(interval, other) for other in intervals)
    
    return min(cs_intervals, key=lambda interval: total_intersection(interval, edits))

def sub_cs(sentence, parser, translator, src_lang="en", tgt_lang="zh-tw", select = 'random', verbose = False):
	# parse the sentence using Benepar
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
		elif select == 'intersect':
			phrase_to_translate, start, end = select_least_intersect(phrases, m2)

		sentence = [leaf.split("|:::|")[0] for leaf in tree.leaves()]

		# translate the selected phrase
		try:
			translation = retry(translator.translate(phrase_to_translate, src=src_lang, dest=tgt_lang), ex_type=httpcore._exceptions.ReadTimeout, limit=10, wait_ms=100, wait_increase_ratio=10, logger=None)
		except httpcore._exceptions.ReadTimeout:
			print ("Timeout Error - Sentence: {}".format(" ".join(sentence)))
			# Return original sentence
			return (sentence, [False]*len(sentence))
		translation = translation.text
		# replace the selected phrase with its translation
		new_sentence = sentence[:start] + [translation] + ["<CS_FILL>"]*(end-start-1) + sentence[end:]
		cs_list = [False] * start + [True] * (end-start) + [False] * (len(sentence)-end)

		if verbose:
			# print the original and translated sentences, and the span
			print(f"Original sentence: {sentence}")
			print(f"Translated sentence: {new_sentence}")
			print(f"Translated span: ({start}, {end})")

		return (new_sentence, cs_list)
	else:
		return (sentence, [False]*len(sentence))
	
def main(args):
	try:
		pid = args[0]
		in_m2 = args[1]
		input_path = args[2]
		with open(input_path + ".p" + str(pid) + ".src", "w+") as src_cache, open(input_path + ".p" + str(pid) + ".src", "w+") as tgt_cache:
			# download and load the Benepar model
			# benepar.download('benepar_en3')
			parser = benepar.Parser('benepar_en3')

			# create a translator object
			translator = Translator()
			output = list()
			tqdm_text = "Batch #" + "{}".format(pid).zfill(3)
			for sentence in in_m2: # tqdm(in_m2, desc=tqdm_text, position=pid+1):
				try:
					if len(sentence["corr"]) > 100:
						# Sentence too long, may cause issues with parser
						# Split sentences
						cs_words = []
						cs_list = []
						current_words = []
						current_list = []
						for token in sentence["corr"]:
							current_words.append(token)
							if token == ".":
								current_words, current_list = sub_cs(current_words, parser, translator)
								cs_words += current_words
								cs_list += current_list
								current_words = []
						if current_words:
							current_words, current_list = sub_cs(current_words, parser, translator)
							cs_words += current_words
							cs_list += current_list
					else:
						cs_words, cs_list = sub_cs(sentence["corr"], parser, translator)
					
					if max([m2_edit[0][1] for m2_edit in sentence["edits"]]) <= len(cs_list):
						incorr = apply_edit_to_cs(cs_words, cs_list, sentence["edits"])

						corr = [i for i in cs_words if i != "<CS_FILL>"]
						incorr = [i for i in incorr if i != "<CS_FILL>"]

						corr = " ".join(corr)
						incorr = " ".join(incorr)

						output.append((incorr, corr))
						src_cache.write(incorr + '\n')
						tgt_cache.write(corr + '\n')
					else:
						print ("Sentence is shorter than m2 edit")
				except Exception as e:
					print (e)
					print (len(sentence["corr"]))
					print ("ERROR processing sentence: {}".format(sentence))
		return output
	except Exception as e:
		print (e)

if __name__ == "__main__":
	if len(sys.argv) != 4:
		print("[USAGE] %s input_inv_m2_file output_cs_incorr output_cs_corr" % sys.argv[0])
		sys.exit()

	# define a sentence to parse and translate
	input_path = sys.argv[1]
	output_cs_incorr_path = sys.argv[2]
	output_cs_corr_path = sys.argv[3]

	if platform.system() == "Darwin":
		multiprocessing.set_start_method('spawn')

	with open(output_cs_incorr_path, "w+") as output_cs_incorr, open(output_cs_corr_path, "w+") as output_cs_corr:
		in_m2  = parse_m2(input_path)
		cpu_count = multiprocessing.cpu_count()
		chunks = list(divide_chunks(list(in_m2.values()), int((len(in_m2)/cpu_count)+1)))
		print ("Total {} Chunks".format(len(chunks)))
		with multiprocessing.Pool(processes=cpu_count, initargs=(multiprocessing.RLock(),), initializer=tqdm.set_lock) as pool:
			# Pool(processes=num_processes, initargs=(RLock(),), initializer=tqdm.set_lock)
			results = pool.map(main, [(i, n, input_path) for i, n in enumerate(chunks)])
		for result in results:
			for ret in result:
				output_cs_incorr.write(ret[0] + '\n')
				output_cs_corr.write(ret[1] + '\n')
