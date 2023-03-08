source venv/bin/activate
error_file="results/error.$2.$1.txt"
results_file="results/results.$2.$1.txt"
temp_file="results/temp.$2.$1.txt"

if [ ! -f data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt ]
then
    eval python predict.py --model_path models/output/$1/best.th \
                    --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/annotated/gold/annotated.en.$2.src.txt \
                    --output_file data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt \
                    --transformer_model xlm-roberta
fi

if [ ! -f data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt ]
then
    eval python predict.py --model_path models/output/$1/best.th \
                    --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/lang8/gold/lang8.en.$2.src.txt \
                    --output_file data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt \
                    --transformer_model xlm-roberta
fi

if [ ! -f data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt ]
then
	eval python predict.py --model_path models/output/$1/best.th \
                --vocab_path models/output/$1/vocabulary --input_file data/corpus/eval/bea19/gold/bea19.dev.en.src.txt \
                --output_file data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt \
                --transformer_model xlm-roberta
fi

source errant_env/bin/activate

echo $1 > $results_file
echo $1 > $error_file

prepattern_error='1,3d'
postpattern_error='$d;N;4,9ba'
prepattern_results='1,3d'
postpattern_results='$d;N;4,5ba'
lang_tag_upper=$(echo "$2" | tr '[:lower:]' '[:upper:]')

if [ -f data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt ]
then
    eval errant_parallel -orig data/corpus/eval/lang8/gold/lang8.en.$2.src.txt -cor data/corpus/eval/lang8/lang8.en.$2.$1.hyp.txt -out data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2

    prefix="\"Lang-8 CS\"    $lang_tag_upper     Span    GEC    "
    eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/gold/lang8.en.$2.m2 -cat 3 > "$temp_file""1"
    sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""1"
    awk -v p="$prefix " '{print p $0}' "$temp_file""1" >> $error_file

    eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/gold/lang8.en.$2.m2 > "$temp_file""2"
    sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""2"
    awk -v p="$prefix " '{print p $0}' "$temp_file""2" >> $results_file

    prefix="\"Lang-8 CS\"    $lang_tag_upper    Span    GED    "
    eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/gold/lang8.en.$2.m2 -cat 3 -ds > "$temp_file""3"
    sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""3"
    awk -v p="$prefix " '{print p $0}' "$temp_file""3" >> $error_file

    eval errant_compare -hyp data/corpus/eval/lang8/lang8.en.$2.$1.hyp.m2 -ref data/corpus/eval/lang8/gold/lang8.en.$2.m2 -ds > "$temp_file""4"
    sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""4"
    awk -v p="$prefix " '{print p $0}' "$temp_file""4" >> $results_file

    rm "$temp_file"*
fi

if [ -f data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt ]
then
    eval errant_parallel -orig data/corpus/eval/annotated/gold/annotated.en.$2.src.txt -cor data/corpus/eval/annotated/annotated.en.$2.$1.hyp.txt -out data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2

    prefix="\"Annotated CS\"    $lang_tag_upper    Span    GEC   "
    eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/gold/annotated.en.$2.m2 -cat 3 >> "$temp_file""1"
    sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""1"
    awk -v p="$prefix " '{print p $0}' "$temp_file""1" >> $error_file

    eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/gold/annotated.en.$2.m2 >> "$temp_file""2"
    sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""2"
    awk -v p="$prefix " '{print p $0}' "$temp_file""2" >> $results_file

    prefix="\"Annotated CS\"    $lang_tag_upper    Span    GED    "
    eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/gold/annotated.en.$2.m2 -cat 3 -ds > "$temp_file""3"
    sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""3"
    awk -v p="$prefix " '{print p $0}' "$temp_file""3" >> $error_file

    eval errant_compare -hyp data/corpus/eval/annotated/annotated.en.$2.$1.hyp.m2 -ref data/corpus/eval/annotated/gold/annotated.en.$2.m2 -ds > "$temp_file""4"
    sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""4"
    awk -v p="$prefix " '{print p $0}' "$temp_file""4" >> $results_file

    rm "$temp_file"*
fi

if [ -f data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt ]
then
    if [ ! -f data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 ]
    then
        eval errant_parallel -orig data/corpus/eval/bea19/gold/bea19.dev.en.src.txt -cor data/corpus/eval/bea19/bea19.dev.en.$1.hyp.txt -out data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2

        prefix="\"BEA-19 Dev\"    EN    Span    GEC   "
        eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/gold/bea19.dev.en.m2 -cat 3 >> "$temp_file""1"
        sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""1"
        awk -v p="$prefix " '{print p $0}' "$temp_file""1" >> $error_file

        eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/gold/bea19.dev.en.m2 >> "$temp_file""2"
        sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""2"
        awk -v p="$prefix " '{print p $0}' "$temp_file""2" >> $results_file

        prefix="\"BEA-19 Dev\"    EN    Span    GED    "
        eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/gold/bea19.dev.en.m2 -cat 3 -ds > "$temp_file""3"
        sed -i -e $prepattern_error -e :a -e $postpattern_error -e 'P;D' "$temp_file""3"
        awk -v p="$prefix " '{print p $0}' "$temp_file""3" >> $error_file

        eval errant_compare -hyp data/corpus/eval/bea19/bea19.dev.en.$1.hyp.m2 -ref data/corpus/eval/bea19/gold/bea19.dev.en.m2 -ds > "$temp_file""4"
        sed -i -e $prepattern_results -e :a -e $postpattern_results -e 'P;D' "$temp_file""4"
        awk -v p="$prefix " '{print p $0}' "$temp_file""4" >> $results_file

        rm "$temp_file"*
    fi
fi