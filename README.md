## CSI Collector

This project collects channel state information (CSI) of Wi-Fi packets using Raspberry Pi with Nexmon CSI tool.
The collected CSI data can be either stored in local device or transferred to a server. 

## Usage

Usage: ```(sudo) python3 main.py [server/client] [options]```

* server/client: determine server of client modes
* option -h host: specify host (e.g., -h 192.168.0.1)
* option -p port: specify port number (e.g., -p 9999)
* option -c channel: specify Wi-Fi channel (e.g., -c 1)
* option -b bandwidth: specify Wi-Fi bandwidth (e.g., -b 40)
* **sudo privilege is required for client mode** as Wi-Fi interface needs to be configured.


For server mode, host and port options are necessary to open server socket. For client mode, channel and bandwidth options are necessary to capture CSI of Wi-Fi packets transmitting on the specified channel. 
However host and port options are optional. If these options are not provided, the collected CSI data will be stored in the local storage instead of transmitting the data to the server.


Examples:

1. (server mode) open server with given IP and port  
``` python3 main.py server -h 192.168.1.1 -p 9999 ```

2. (client mode) Collect CSI of Wi-Fi packets transmitting on channel 1 with 20 MHz bandwidth and transfer the collected results to the host  
``` sudo python3 main.py client -h 192.168.1.1 -p 9999 -c 1 -b 20 ```

3. (client mode) Collect CSI and store the results to the local device  
```sudo python3 main.py client -c 1 b -20```


## Installation
1. To use Nexmon CSI tool, we recommend to configure Raspberry Pi by following the instructions in this link: https://github.com/nexmonster/nexmon_csi/tree/pi-5.10.92  
2. Scapy python library is additionally required to capture UDP packets, which carry CSI data: 
```sudo pip install scapy``` or ```sudo apt install python3-scapy```


## Analyzing the CSI

The collected CSI data will be stored in a text file under 'measured_data' folder.
Matlab scripts can be used to parse collected CSI data. Please run ```plot_all_csi.m``` script to see some results.


## Contact 
Jeongsik Choi (jeongsik.choi@knu.ac.kr)
