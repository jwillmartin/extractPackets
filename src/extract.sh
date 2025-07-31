#!/bin/bash

#this takes the location of the executed script as opposed to the current location
#this allows it to be run anywhere
directory="`dirname \"$0\"`"
directory="`( cd \"$directory\" && cd ../ && pwd )`"
cd $directory

mkdir -p data
cd data
mkdir -p tsharkOutput
mkdir -p payloadOutput
mkdir -p decodedOutput

cd $directory

printf "\nWhat type of J2735 message was captured?\n"
printf "MAP\nSPAT\nBSM\nPSM\nSDSM\nTIM\nMobility\nTraffic Control\n\n"
IFS= read -r messageType

if [ "$messageType" == "MAP" ]; then
	messageTypeID=0012
elif [ "$messageType" == "SPAT" ]; then
	messageTypeID=0013
elif [ "$messageType" == "BSM" ]; then
	messageTypeID=0014
elif [ "$messageType" == "PSM" ]; then
	messageTypeID=0020
elif [ "$messageType" == "SDSM" ]; then
	messageTypeID=0029
elif [ "$messageType" == "TIM" ]; then
	messageTypeID=001f
elif [ "$messageType" == "Mobility" ]; then
	printf "\nRequest, Response, Path, or Operation?\n"
	read messageSecond
	if [ $messageSecond == "Request" ]; then
		messageTypeID=00f0
	elif [ $messageSecond == "Response" ]; then
		messageTypeID=00f1
	elif [ $messageSecond == "Path" ]; then	
		messageTypeID=00f2
	elif [ $messageSecond == "Operation" ]; then
		messageTypeID=00f3
	else 
		echo "Invalid J2735 message type..."
		exit
	fi
	messageType+=" $messageSecond"
elif [ "$messageType" == "Traffic Control" ]; then
	echo "Request or Message?"
	read messageSecond
	if [ $messageSecond == "Request" ]; then
		messageTypeID=00f4
	elif [ $messageSecond == "Message" ]; then	
		messageTypeID=00f5
	else 
		echo "Invalid J2735 message type..."
		exit
	fi
	messageType+=" $messageSecond"
else echo "Invalid J2735 message type..."
	exit
fi

payloadType="hex"
messageTypeIdFound=false


searchForMessageTypeIdInFile() {
	fileCheck=$1
	messageTypeIdToFind=$2
	numPacketsToCheck=$3
	messageTypeIdFound=false

	echo
	#check the first 10 packets for the desired message type ID
	for (( c=1; c<=$numPacketsToCheck; c++ )); do
		currentPayload=$(sed '$cq;d' $fileCheck | awk -F ',' '{print $2}')
		if [[ "$currentPayload" == *"$messageTypeIdToFind"* ]]; then
			messageTypeIdFound=true
			echo "Found desired message ID ($messageTypeIdToFind) in packet $c"
			break
		fi
	done
}


extractPackets() { 
	echo
	cd $directory/data
	ls *.pcap
	echo 

	while true; do
		read -rep "Input filename from list: " fileRead
		filePrefix="${fileRead//.pcap/}"
		fileWrite="${filePrefix}_${messageType}.csv"
		if [ ! -f $fileRead ]; then
			echo "File not found!"
		else
			break
		fi
	done

	tshark -r $fileRead --disable-protocol wsmp -Tfields -Eseparator=, -e frame.time_epoch -e data.data > $directory/data/tsharkOutput/$fileWrite

	searchForMessageTypeIdInFile $directory/data/tsharkOutput/$fileWrite $messageTypeID 10

	if [ $messageTypeIdFound == true ]; then
			# The first packet contains the message id
			printf "\nSuccessfully decoded pcap into hex payloads\n"
			payloadType="hex"
	else
			# The first packet does not contain the message id. This is most likely becuase payload is contained in ASCII
			printf "\nCould not find message ID in hex decoded payloads, trying ascii\n"
			tshark -r $fileRead -o data.show_as_text:TRUE --disable-protocol wsmp -T fields -E separator=, -e frame.time_epoch -e data.text > $directory/data/tsharkOutput/$fileWrite
			payloadType="ascii"
			
			searchForMessageTypeIdInFile $directory/data/tsharkOutput/$fileWrite $messageTypeID 10
			
			if [ $messageTypeIdFound ]; then
				printf "\nSuccessfully decoded pcap into ascii payloads\n\n"
			else
				printf "\nDecoding in ascii still resulted in an empty file, exiting...\n"
				exit
			fi
			
	fi 
}


getPayload() {
	cd $directory/data/tsharkOutput
	# parse tshark output to get rid of unnecessary bytes in front of payloads
	for i in *; do
		python3 $directory/src/tshark_OutputParser.py $i $messageType $payloadType
	done
	mv *_payload.csv $directory/data/payloadOutput
	rm *
}


decodePackets() {
	cd $directory/data/payloadOutput
	printf 'Decoding.\n'
	for i in $(find . -name "*${messageType}_payload.csv"); do
		file=$(basename -- "$i")
		fileName="decoded_${file%.*}.csv"
		echo "$fileName"
		python3 $directory/src/decoder.py $i ${fileName} "$messageType" $messageTypeID
	done

	mv *decoded* $directory/data/decodedOutput
	rm *
	printf 'Complete.\n'
}


processing() {
	extractPackets
	getPayload
	decodePackets
}

processing
