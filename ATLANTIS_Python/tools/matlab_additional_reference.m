cd(fileparts(fileparts(mfilename('fullpath'))));sourceRoot=fullfile(pwd,'original','ATLANTIS','Toolbox');if ~exist(sourceRoot,'dir'),sourceRoot=fullfile(pwd,'reference','Toolbox');end;addpath(genpath(sourceRoot));set(0,'DefaultFigureVisible','off');
try
 opts=struct('Display','off','Input','raw','MaxHalves',40,'MaxIter',1,'TolFun',1e-9,'Initialisation','pca');x=diag([1 2 3]);[xy,stress]=sammonMapping(x,2,opts);save('validation/matlab_sammon_step.mat','x','xy','stress','-v7');
 maps=struct;names={'jet','hot','spring','summer','autumn','winter','cool','gray','hsv','prism','parula'};
 for i=1:numel(names),for n=[1 4 100],maps.([names{i} '_' num2str(n)])=feval(names{i},n);end;end
 parula_base=parula(256);save('validation/matlab_colors.mat','maps','parula_base','-v7');
catch e,disp(getReport(e));end
close all force;
