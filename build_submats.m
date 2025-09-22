function build_submats(configPath)
%BUILD_SUBMATS  AIRの公式 load_air(airpar) を用いて、中間 .mat (IR[M=1,R,N]) を一括生成
% - 公式 load_air.m / data/ は無改変・相対パスのまま使用（呼び出し時に一時 cd）
% - 角度は実在パターンのみ自動生成（room=5: 0:15:180, room=11 & rir_no=3: 0:45:180）
% - config.yaml/json があれば読み込み、無ければデフォルト値で実行
%
% 使い方:
%   >> build_submats                 % ./config.yaml or ./config.json を読む（無ければデフォルト）
%   >> build_submats('myconf.yaml')  % 明示指定
%
% 出力: out_intermediate/AIR_rirtype{d}_room{d}_head{d}_rirno{d}_az{d}_R{d}.mat
%       （変数: IR[M=1,R,N], fs, rir_type, room, head, rir_no, azimuth）

    if nargin < 1 || isempty(configPath)
        configPath = fullfile(pwd, 'config.yaml');
    end

    % --- 設定ロード（YAML→JSONフォールバック→デフォルト） ---
    cfg = local_read_config_or_default(configPath);

    % --- outフォルダ作成 ---
    outDir = cfg.out_intermediate;
    if ~exist(outDir, 'dir'); mkdir(outDir); end

    % --- 公式 load_air の場所を特定（相対 data/ を成立させるため） ---
    assert(exist('load_air','file')==2, 'load_air が見つかりません（パスを確認）');
    load_air_path = which('load_air');
    load_air_dir  = fileparts(load_air_path);
    assert(isfolder(fullfile(load_air_dir,'data')), ...
        'load_air と同階層に data/ が見当たりません: %s', load_air_dir);

    % --- ループ対象（数値配列へ正規化） ---
% --- ループ対象（数値配列へ正規化） ---
    rooms   = double(cfg.rooms(:)).';

    % ★ rir_type=1 のとき、roomごとの既定rir_no集合を自動で与える
    if isempty(cfg.rir_no_list)
        % 部屋ごとの距離（コメントの順序で番号付け：1..end）
        rirnos_by_room = containers.Map('KeyType','double','ValueType','any');
        rirnos_by_room(1) = 1:3;                  % booth: {0.5,1,1.5} → 3つ
        rirnos_by_room(2) = 1:3;                  % office: {1,2,3} → 3つ
        rirnos_by_room(3) = 1:5;                  % meeting: {1.45,1.7,1.9,2.25,2.8} → 5つ
        rirnos_by_room(4) = 1:6;                  % lecture: {2.25,4,5.56,7.1,8.68,10.2} → 6つ
        rirnos_by_room(5) = 1:3;                  % stairway: {1,2,3} → 3つ
        rirnos_by_room(11)= 1:6;                  % aula_carolina: {1,2,3,5,15,20} → 6つ
    else
        % 明示指定があればそれを全部屋に適用
        rirnos_by_room = containers.Map('KeyType','double','ValueType','any');
        for rr = rooms
            rirnos_by_room(rr) = double(cfg.rir_no_list(:)).';
        end
    end

    % ★ head を単一値/配列どちらでも受ける
    if isfield(cfg,'head_list') && ~isempty(cfg.head_list)
        head_list = double(cfg.head_list(:)).';
    else
        head_list = double(cfg.head(:)).';
    end

    chanmap = double(cfg.chan_map(:)).';
        % --- メインループ ---
    for room = rooms
        rirnos = rirnos_by_room(room);

        for head = head_list
            for rir_no = rirnos

                % 実在パターンに基づく azimuth リスト（上書きがあれば優先）
                if isfield(cfg, 'az_list_override') && ~isempty(cfg.az_list_override)
                    az_list = double(cfg.az_list_override(:)).';
                else
                    az_list = local_az_list_for(cfg.rir_type, room, rir_no);
                end

                for az = az_list
                    R = numel(chanmap);
                    IR_cells = cell(1,R);
                    fs_ref = [];

                    % --- L/Rそれぞれ取得 ---
                    for r = 1:R
                        here = pwd;
                        cleanupObj = onCleanup(@() cd(here)); %#ok<NASGU>
                        cd(load_air_dir);

                        airpar = struct('fs', cfg.fs, ...
                                        'rir_type', cfg.rir_type, ...
                                        'room', room, ...
                                        'channel', chanmap(r));

                        % ★ binaural 固定
                        airpar.head    = head;
                        airpar.rir_no  = rir_no;
                        airpar.azimuth = az;
                        if room == 11
                            airpar.mic_type = 3; % 明示
                        end

                        try
                            [h, info] = load_air(airpar);
                        catch ME
                            if cfg.verbose
                                warning('[skip] room=%d head=%d rir_no=%d az=%g ch=%d | %s', ...
                                        room, head, rir_no, az, chanmap(r), ME.message);
                            end
                            h = []; info = struct('fs', cfg.fs);
                        end

                        if isempty(h)
                            IR_cells{r} = [];
                        else
                            IR_cells{r} = h(:).';
                            if isempty(fs_ref)
                                if isstruct(info) && isfield(info,'fs'), fs_ref = info.fs;
                                else, fs_ref = cfg.fs; end
                            end
                        end
                    end

                    % --- 保存条件：両ch必須 or 片chでも可 ---
                    present = ~cellfun(@isempty, IR_cells);
                    if cfg.require_full_stereo
                        if ~all(present)
                            if cfg.verbose
                                fprintf('[skip stereo-missing] room=%d head=%d rir_no=%d az=%g (ch欠落)\n', ...
                                        room, head, rir_no, az);
                            end
                            continue;
                        end
                    else
                        if all(~present)
                            if cfg.verbose
                                fprintf('[skip all] room=%d head=%d rir_no=%d az=%g (全ch失敗)\n', ...
                                        room, head, rir_no, az);
                            end
                            continue;
                        end
                    end

                    % --- [M=1,R=2,N] へ整形 ---
                    N = max(cellfun(@numel, IR_cells));
                    IR = zeros(1, R, N);
                    for r = 1:R
                        x = IR_cells{r};
                        if ~isempty(x)
                            IR(1,r,1:numel(x)) = x;
                        end
                    end

                    % --- 保存 ---
                    fs       = fs_ref;
                    rir_type = cfg.rir_type;
                    azimuth  = az;

                    fname = sprintf('AIR_rirtype%d_room%d_head%d_rirno%d_az%d_R%d.mat', ...
                                    rir_type, room, head, rir_no, azimuth, R);
                    matpath = fullfile(outDir, fname);
                    save(matpath, 'IR','fs','rir_type','room','head','rir_no','azimuth','-v7');

                    if cfg.verbose
                        fprintf('[Saved] %s | R=%d, N=%d, fs=%d\n', matpath, R, N, fs);
                    end
                end
            end
        end
    end
end

%==== helpers ===============================================================

function cfg = local_read_config_or_default(path)
    % 既定値
% 既定値
    cfg = struct( ...
        'out_intermediate', fullfile(pwd,'out_intermediate'), ...
        'fs',        48000, ...
        'rir_type',  1, ...        % ★ 11 → 1 に修正（binaural）
        'rooms',     [1 2 3 4 5 11], ...
        'head',      1, ...
        'head_list', [0 1], ...    % ★ 追加：with/without dummy head を総当たり
        'rir_no_list', [], ...     % ★ 空なら部屋ごとに自動決定
        'chan_map',  [1 0], ...    % ★ L(1),R(0)の順で保存（[M=1,R=2,N]）
        'require_full_stereo', true, ... % ★ 追加：両chが揃った時だけ保存
        'verbose',   true, ...
        'mock_up_type', 1, ...
        'phone_pos',   1, ...
        'az_list_override', [] ... % 既存
    );

    if isfile(path)
        s = local_try_read_yaml_or_json(path);
        if ~isempty(s)
            % キーの別名吸収
            s = local_alias_normalize(s);
            % マージ（sで上書き）
            f = fieldnames(s);
            for i=1:numel(f)
                cfg.(f{i}) = s.(f{i});
            end
        end
    else
        % 同名 .json フォールバック
        [p,f,~] = fileparts(path);
        jsonPath = fullfile(p, [f '.json']);
        if isfile(jsonPath)
            s = local_try_read_yaml_or_json(jsonPath);
            s = local_alias_normalize(s);
            f = fieldnames(s);
            for i=1:numel(f)
                cfg.(f{i}) = s.(f{i});
            end
        end
    end
end

function s = local_try_read_yaml_or_json(path)
    s = struct();
    [~,~,ext] = fileparts(path);
    switch lower(ext)
        case {'.yml','.yaml'}
            if exist('yamlread','file')
                s = yamlread(path);
            elseif exist('ReadYaml','file')
                s = ReadYaml(path);
            else
                % YAMLパーサが無ければ空を返す（上位でJSONにフォールバック）
                return;
            end
        case '.json'
            txt = fileread(path);
            s = jsondecode(txt);
        otherwise
            return;
    end
end

function s = local_alias_normalize(s)
    % Fs→fs などの別名を正規化
    aliases = struct('Fs','fs','RirType','rir_type','Rooms','rooms','Head','head', ...
                     'RirNoList','rir_no_list','ChanMap','chan_map', ...
                     'OutIntermediate','out_intermediate', ...
                     'MockUpType','mock_up_type','PhonePos','phone_pos', ...
                     'AzListOverride','az_list_override');
    fn = fieldnames(aliases);
    for i=1:numel(fn)
        a = fn{i}; b = aliases.(a);
        if isfield(s,a) && ~isfield(s,b); s.(b) = s.(a); end
    end
end

function az = local_az_list_for(rir_type, room, rir_no)
    % 実在パターン: 論文/配布に基づく最小集合
    if rir_type == 1
        if room == 5
            az = 0:15:180;                 % stairway は方位スイープ
        elseif room == 11 && rir_no == 3
            az = 0:45:180;                 % Aula Carolina の 3m は方位スイープ
        else
            az = 90;                       % ★既定は正面（AIRで 90°）
        end
    else
        az = 0;
    end
end