source venv/bin/activate

eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/annotated/annotated.en.$2.src.txt \
                --output_file data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt \
                --transformer_model xlm-roberta

eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/lang8/lang8.en.$2.src.txt \
                --output_file data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt \
                --transformer_model xlm-roberta

eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/bea19/bea19.dev.en.src.txt \
                --output_file data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt \
                --transformer_model xlm-roberta

source errant_env/bin/activate

eval errant_parallel -orig data/corpus/eval/annotated/annotated.en.$2.src.txt -cor data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt -out data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2
eval errant_parallel -orig data/corpus/eval/lang8/lang8.en.$2.src.txt -cor data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt -out data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2
eval errant_parallel -orig data/corpus/eval/bea19/bea19.dev.en.src.txt -cor data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt -out data/corpus/eval/bea19/bea19.dev.$1.hyp.m2

echo $1 > results.$1.txt

echo "\"Lang-8 CS\"    $2    Span    GEC" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/lang8.en.$2.m2 -cat 3 >> results.$2.$1.txt

echo "\"Lang-8 CS\"    $2    Span    GED" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/lang8.en.$2.m2 -cat 3 -ds >> results.$2.$1.txt

echo "\"Annotated CS\"    $2    Span    GEC" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/annotated.en.$2.m2 -cat 3 >> results.$2.$1.txt

echo "\"Annotated CS\"    $2    Span    GED" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/annotated.en.$2.m2 -cat 3 -ds >> results.$2.$1.txt

echo "\"BEA-19 Dev\"    EN    Span    GEC" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/bea19.dev.en.m2 -cat 3 >> results.$2.$1.txt

echo "\"BEA-19 Dev\"    EN    Span    GED" >> results.$2.$1.txt
eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/bea19.dev.en.m2 -cat 3 -ds >> results.$2.$1.txt
