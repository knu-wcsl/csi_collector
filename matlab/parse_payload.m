function result = parse_payload(payload, verbose)
    % this function decodes payload which is a string of hex stream
    % decoding rule can be found in the link below
    % https://github.com/seemoo-lab/nexmon_csi

    % result will be returned as a struct where each field is as follow
    %   flag_csi_available: 0 (unavailable), 1 (available)
    %   rssi: received signal strength
    %   frame_control: frame control 
    %   source_mac: mac address of source device which transmited the packet
    %   seq_num: sequence number of Wi-Fi frame
    %   core_num: core number in case that multiple cores are used
    %   stream_num: spatial stream number in case that multiple antennas are used
    %   chip_ver: chip version
    %   csi: csi (complex values)

    % set default input
    if ~exist('verbos', 'var')
        verbose = 0;
    end

    % prepare output 
    result = struct('flag_csi_available', 0);

    %% Parse payload
    % check the length of payload
    if length(payload) < 36
        if verbose
            disp('[Warning] not enough payload length');
        end
        return;
    end

    % check magic bytes (2 bytes)
    if ~strcmp(payload(1:4), '1111')
        if verbose
            disp('[Warning] magic bytes do not match');
        end
        return;
    end

    % rssi (1 byte - two's complement)
    rssi = hex2dec(payload(5:6));
    if rssi >= 128
        rssi = rssi - 2^8;
    end
    result.rssi = rssi;

    % frame control (1 byte)
    result.frame_control = hex2dec(payload(7:8));

    % source mac (6 bytes)
    result.source_mac = strjoin({payload(9:10),payload(11:12),payload(13:14),payload(15:16),payload(17:18),payload(19:20)}, ':');
    
    % sequence number (2 bytes)
    % - looks like first 12 bits represent number (need to be confirmed)
    result.seq_num = bitshift(hex2dec(swap_hex(payload(21:24))), -1);
    
    % core & spatial (2 bytes)
    % - lowest 3 bits represent core number
    % - next 3 bits represent spatial stream number
    core_ss = hex2dec(swap_hex(payload(25:28)));
    result.core_num = bitand(0x07, core_ss);
    result.stream_num = bitshift(bitand(0x38, core_ss), -3);

    % channel spec (2 bytes)
    result.ch_spec = swap_hex(payload(29:32));

    % chip ver (2 bytes)
    result.chip = swap_hex(payload(33:36));

    % channel state information
    n_csi = (length(payload) - 36) / 8;
    if (n_csi == 64) || (n_csi == 128) || (n_csi == 256)
        csi_dat = payload(37 : 36 + n_csi * 8);
        csi = zeros(2*n_csi, 1);
        for k=1:2*n_csi
            csi(k) = hex2dec(swap_hex(csi_dat(4*k-3:4*k)));
        end
        csi(csi > 2^15) = csi(csi > 2^15) - 2^16;
        csi = csi(1:2:end) + 1i*csi(2:2:end);

        result.csi = csi;
        result.flag_csi_available = 1;
    else
        if verbose
            disp(['Warning: unexpected csi number: ', num2str(n_csi)]);
        end
        return;
    end
end


function h_new = swap_hex(h)    % swap 2bytes hex string (e.g., '00AB' -> 'AB00')
    h_new = [h(3:4), h(1:2)];
end
