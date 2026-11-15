cd(fileparts(fileparts(mfilename('fullpath'))));
root = fullfile(pwd,'original','ATLANTIS','Toolbox');
addpath(genpath(root));
out = fullfile(pwd,'validation','guide_v7'); mkdir(out);
files = strsplit(genpath(root),pathsep);
for i=1:numel(files)
 fs=dir(fullfile(files{i},'*.fig'));
 for j=1:numel(fs)
  p=fullfile(files{i},fs(j).name);
  data=load(p,'-mat'); save(fullfile(out,[fs(j).name '.mat']),'-struct','data','-v7');
 end
end
fid=fopen(fullfile(pwd,'validation','matlab_ready.txt'),'w'); fprintf(fid,'MATLAB %s\n',version); fclose(fid);

