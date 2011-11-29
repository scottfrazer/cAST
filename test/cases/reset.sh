for file in *
do
  rm $file/preprocessed $file/pptok $file/ppparse $file/ppast $file/ctok $file/cparse $file/cast 2>/dev/null
done
