# Mobile-App-Failover
This script continuously checks the health of your primary Couchbase Sync Gateway using a simple HEAD request to the /_ping endpoint. If the primary app services cluster (not the endpoint) fails more than nine times in a row, it automatically attempts to switch over (“fail over”) to the secondary app services cluster—provided the secondary is healthy. The checks run in the background on a timer, and everything is logged so you can see status updates, failure counts, and whether a failover took place. 

This ensures your application stays available even if one cluster becomes unreachable. This code is provided as an example only. You may need to modify or extend it to meet the specific requirements and failover logic of your production environment. 

