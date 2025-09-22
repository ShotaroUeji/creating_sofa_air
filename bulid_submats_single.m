% test.m

clear; close all; clc

% === 出力先を絶対パスで定義（ここを書き換えてOK） ===
outDir = fullfile(pwd, "out_mat");   % 今のフォルダ配下に out/ を作って保存
if ~exist(outDir, 'dir'); mkdir(outDir); end

fs = 48000;
airpar = struct('fs',fs,'rir_type',1,'room',11,'head',1,'rir_no',3,'azimuth',45);

% --- L/R 読み込み ---
airpar.channel = 1;  % Left
[hL, infoL] = load_air(airpar);
airpar.channel = 0;  % Right
[hR, infoR] = load_air(airpar);

% --- 形状＆中身の簡易チェック ---
fprintf('hL: %d samples, fs=%g | hR: %d samples, fs=%g\n', ...
    numel(hL), infoL.fs, numel(hR), infoR.fs);

% --- [M=1, R=2, N] に整形 ---
N = max(numel(hL), numel(hR));
IR = zeros(1, 2, N);
IR(1,1,1:numel(hL)) = hL(:).';
IR(1,2,1:numel(hR)) = hR(:).';

azimuth = 45;      % ソース方位（水平）
rir_type = 1;
room = 11;
head = 1;
rir_no = 3;



% --- 保存（絶対パス） ---
outPath = fullfile(outDir, sprintf('AIR_rirtype%d_room%d_head%d_rirno%d_az%d_subset.mat', rir_type, room, head, rir_no, azimuth));
save(outPath, 'IR', 'fs', 'rir_type', 'room', 'head', 'rir_no', 'azimuth', '-v7');

% --- 保存できたか検証 ---
fprintf('Saved: %s\n', outPath);
disp(dir(outPath));               % ファイルの存在とサイズを表示
whos('-file', outPath)            % ファイル内の変数一覧を表示

% --- ついでに波形を確認（任意） ---
figure; 
subplot(2,1,1); plot(squeeze(IR(1,1,:))); title('Left IR'); xlabel('samples');
subplot(2,1,2); plot(squeeze(IR(1,2,:))); title('Right IR'); xlabel('samples');
