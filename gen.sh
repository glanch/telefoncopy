# Row 1
sox -n sounds/tone_1.wav synth 0.3 sine 697 sine 1209
sox -n sounds/tone_2.wav synth 0.3 sine 697 sine 1336
sox -n sounds/tone_3.wav synth 0.3 sine 697 sine 1477

# Row 2
sox -n sounds/tone_4.wav synth 0.3 sine 770 sine 1209
sox -n sounds/tone_5.wav synth 0.3 sine 770 sine 1336
sox -n sounds/tone_6.wav synth 0.3 sine 770 sine 1477

# Row 3
sox -n sounds/tone_7.wav synth 0.3 sine 852 sine 1209
sox -n sounds/tone_8.wav synth 0.3 sine 852 sine 1336
sox -n sounds/tone_9.wav synth 0.3 sine 852 sine 1477

# Row 4
sox -n sounds/tone_star.wav synth $len sine 941 sine 1209
sox -n sounds/tone_0.wav synth $len sine 941 sine 1336
sox -n sounds/tone_pund.wav synth $len sine 941 sine 1477

# Wählton 
sox -n sounds/waehlton.wav synth 30 sine 425

# Ringback
sox -n sounds/ringback_de.wav synth 1 sine 425 : synth 4 sine 0

# Busy
sox -n sounds/busy_de.wav synth 0.25 sine 425 : synth 0.25 sine 0 repeat 10