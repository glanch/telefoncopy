
generate_key() {
  local suffix="$1"
  local length="$2"
  sox -n dtmf-1$suffix.wav synth $length sine 697 sine 1209 channels 1
  sox -n dtmf-2$suffix.wav synth $length sine 697 sine 1336 channels 1
  sox -n dtmf-3$suffix.wav synth $length sine 697 sine 1477 channels 1
  sox -n dtmf-4$suffix.wav synth $length sine 770 sine 1209 channels 1
  sox -n dtmf-5$suffix.wav synth $length sine 770 sine 1336 channels 1
  sox -n dtmf-6$suffix.wav synth $length sine 770 sine 1477 channels 1
  sox -n dtmf-7$suffix.wav synth $length sine 852 sine 1209 channels 1
  sox -n dtmf-8$suffix.wav synth $length sine 852 sine 1336 channels 1
  sox -n dtmf-9$suffix.wav synth $length sine 852 sine 1477 channels 1
  
  sox -n dtmf-0$suffix.wav synth $length sine 941 sine 1209 channels 1
  sox -n dtmf-star$suffix.wav synth $length sine 941 sine 1336 channels 1
  sox -n dtmf-pound$suffix.wav synth $length sine 941 sine 1477 channels 1
  
  sox -n dtmf-A$suffix.wav synth $length sine 697 sine 1633 channels 1
  sox -n dtmf-B$suffix.wav synth $length sine 770 sine 1633 channels 1
  sox -n dtmf-C$suffix.wav synth $length sine 852 sine 1633 channels 1
  sox -n dtmf-D$suffix.wav synth $length sine 941 sine 1633 channels 1
}

generate_key "" "0.1"
generate_key "-short" "0.03"

sox -n dtmf-us-busy.wav synth 10 sine 480 sine 620 channels 1
sox -n dtmf-rbt-US.wav synth 10 sine 440 sine 480 channels 1
sox -n dtmf-uk-us-dialtone.wav synth 11 sine 350 sine 440 channels 1
sox -n dtmf-uk-busy.wav synth 10 sine 400 channels 1
sox -n dtmf-uk-ringback.wav synth 10 sine 450 channels 1


sox -n dtmf-eur-dialtone.wav synth 300 sine 425 channels 1
sox -n dtmf-eur-busy.wav synth 10 sine 425 channels 1
sox -n dtmf-eur-ringback.wav synth 1 sine 425 : synth 3 sine 0