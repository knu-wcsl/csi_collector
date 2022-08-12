clear;clc;tic;close all;

foldername = '.\..\measured_data';
filename = 'client_dca632533520_220812_065053.txt';     % ch1, 20MHz
% filename = 'client_dca632533520_220812_084426.txt';     % ch132, 80MHz


%% identify server/client
tmp = strsplit(filename,'_');
if strcmp(tmp{1}, 'server')     % server
    flag_server = 1;
else                            % client
    flag_server = 0;
    dest_mac = strjoin({tmp{2}(1:2),tmp{2}(3:4),tmp{2}(5:6),tmp{2}(7:8),tmp{2}(9:10),tmp{2}(11:12)}, ':');
end


%% open file and read data
fid = fopen([foldername, '\', filename]);

figure; hold on;
while ~feof(fid)
    line = fgetl(fid);
    tmp = strsplit(line, ', ');

    if flag_server
        t1 = str2double(tmp{1});    % client local timestamp when CSI was collected
        t2 = str2double(tmp{2});    % client local timestamp when CSI was transmitted to the server
        t3 = str2double(tmp{3});    % server local timestamp when CSI was written to the file
        dest_mac = tmp{4};
        payload = tmp{5};
    else
        t1 = str2double(tmp{1});    % client local time stamp when CSI was collected
        payload = tmp{2};
    end
    
    % parse payload
    result = parse_payload(payload);
    
    if result.flag_csi_available
        plot(abs(result.csi));
    end
end
fclose(fid);

set(gca, 'YLim', [0, 2048]);


