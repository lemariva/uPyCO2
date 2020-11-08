
#! /bin/bash
echo "starting the service ..."
python restapi.py --port $PORT --project $PROJ_NAME --subscription $PROJ_SUBS

# wait forever not to exit the container
#while true
#do
#  tail -f /dev/null & wait ${!}
#done

exit 0