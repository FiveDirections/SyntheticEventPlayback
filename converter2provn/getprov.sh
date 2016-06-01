Red='\033[0;31m'
Color_Off='\033[0m'

current=`pwd`

[ -d $current/raw_outputs/ ] || mkdir $current/raw_outputs/
cd $current/raw_outputs/


for f in *.raw;
do
  fn=$(basename "$f")
  ext="${fn##*.}"
  fn="${fn%.*}"

  echo "Processing ${Red}$fn${Color_Off}..."

  python ../converter.py $f $fn.provn

  gzip $fn.provn

done

cd $current
