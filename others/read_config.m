function cfg = read_config(path)
%READ_CONFIG  YAML/JSON の設定を struct で返す
% 使い方:  cfg = read_config('config.yaml');  % or .json
% 依存: (あれば) yamlread / ReadYaml。無ければ同名 .json に自動フォールバック。

if nargin < 1 || isempty(path)
    path = fullfile(pwd,'config.yaml');
end
if ~isfile(path)
    % 同名 .json を探す
    [p,f,~] = fileparts(path);
    jsonPath = fullfile(p, [f '.json']);
    if isfile(jsonPath)
        path = jsonPath;
    else
        error('Config not found: %s (or %s)', path, jsonPath);
    end
end

[~,~,ext] = fileparts(path);
switch lower(ext)
    case {'.yml','.yaml'}
        if exist('yamlread','file')
            s = yamlread(path);
        elseif exist('ReadYaml','file')
            s = ReadYaml(path);     % File Exchange: yamlmatlab
        else
            % YAMLパーサが無い → 同名 .json を試す
            [p,f,~] = fileparts(path);
            jsonPath = fullfile(p, [f '.json']);
            if isfile(jsonPath)
                txt = fileread(jsonPath); s = jsondecode(txt);
            else
                error(['YAML parser not found. Install "yamlmatlab" (ReadYaml) ' ...
                       'or place a JSON config next to YAML: %s'], jsonPath);
            end
        end
    case '.json'
        txt = fileread(path); s = jsondecode(txt);
    otherwise
        error('Unsupported config extension: %s', ext);
end

% 型を struct に整形
if isa(s,'struct')
    cfg = s;
elseif istable(s)
    cfg = table2struct(s);
else
    error('Unsupported config content type: %s', class(s));
end

% 別名キーを吸収（Fs→fs など）
alias = struct('Fs','fs','RirType','rir_type','Rooms','rooms','Head','head', ...
               'RirNoList','rir_no_list','AzList','az_list','ChanMap','chan_map', ...
               'OutIntermediate','out_intermediate');
fn = fieldnames(alias);
for i = 1:numel(fn)
    a = fn{i}; b = alias.(a);
    if isfield(cfg,a) && ~isfield(cfg,b); cfg.(b) = cfg.(a); end
end
end
