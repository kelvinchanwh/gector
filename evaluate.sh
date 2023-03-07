source venv/bin/activate

eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/annotated/annotated.en.zh.src.txt \
                --output_file data/corpus/eval/annotated/annotated.en.zh.$1.hyp.txt \
                --transformer_model xlm-roberta

eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/lang8/lang8.en.zh.src.txt \
                --output_file data/corpus/eval/lang8/lang8.en.zh.$1.hyp.txt \
                --transformer_model xlm-roberta

source errant_env/bin/activate


eval errant_parallel -orig data/corpus/eval/lang8/lang8.en.zh.src.txt -cor data/corpus/eval/lang8/lang8.en.zh.$1.hyp.txt -out data/corpus/eval/lang8/lang8.en.zh.$1.hyp.m2
eval errant_parallel -orig data/corpus/eval/annotated/annotated.en.zh.src.txt -cor data/corpus/eval/annotated/annotated.en.zh.$1.hyp.txt -out data/corpus/eval/annotated/annotated.en.zh.$1.hyp.m2

echo $1 > results.$1.txt

echo "\"Lang-8 CS\"    Span    GEC" >> results.$1.txt
eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.zh.$1.hyp.m2 -ref data/corpus/eval/lang8/lang8.en.zh.m2 -cat 3 >> results.$1.txt

echo "\"Lang-8 CS\"    Span    GED" >> results.$1.txt
eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.zh.$1.hyp.m2 -ref data/corpus/eval/lang8/lang8.en.zh.m2 -cat 3 -ds >> results.$1.txt

echo "\"Annotated CS\"    Span    GEC" >> results.$1.txt
eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.zh.$1.hyp.m2 -ref data/corpus/eval/annotated/annotated.en.zh.m2 -cat 3 >> results.$1.txt

echo "\"Annotated CS\"    Span    GED" >> results.$1.txt
eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.zh.$1.hyp.m2 -ref data/corpus/eval/annotated/annotated.en.zh.m2 -cat 3 -ds >> results.$1.txt
