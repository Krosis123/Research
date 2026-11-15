cd(fileparts(fileparts(mfilename('fullpath')))); sourceRoot=fullfile(pwd,'original','ATLANTIS','Toolbox');if ~exist(sourceRoot,'dir'),sourceRoot=fullfile(pwd,'reference','Toolbox');end;addpath(genpath(sourceRoot));set(0,'DefaultFigureVisible','off');
try
 rng(83); x=double(rand(12,5)>.5); x=unique(x,'rows'); [xy,stress]=sammonMapping(x);save('validation/matlab_sammon_valid.mat','x','xy','stress','-v7');
 p=rand(14,2);v=sin(p(:,1)*4)+cos(p(:,2)*3);q=rand(20,2);z=griddata(p(:,1),p(:,2),v,q(:,1),q(:,2),'natural');save('validation/matlab_natural.mat','p','v','q','z','-v7');
 data=load('validation/matlab_yeast_deterministic.mat');n=NetworkDataStructure;n.NetworkType='WeightsBased';n.NodeNames=data.nodeNames;n.NodeCount=numel(data.nodeNames);n.AttractorTable=data.attractorTable;n.NetworkStateList=data.states;n.FileName='Yeast - ';n.CellFateLandscape={'A',.62;'B',.23;'C',.10;'D',.05};
 plot_CellFateLandscape(n,'Cell Fate Landscape',1,1,'jet',n.CellFateLandscape);
 f=gcf; print(f,'validation/matlab_treemap.png','-dpng','-r120');
 patches=findobj(f,'type','patch');rectangles=[];colors=[];
 for k=1:numel(patches)
  c=get(patches(k),'FaceColor');if isnumeric(c), xx=get(patches(k),'XData'); yy=get(patches(k),'YData');rectangles(end+1,:)=[min(xx) min(yy) max(xx)-min(xx) max(yy)-min(yy)];colors(end+1,:)=c;end
 end
 save('validation/matlab_treemap.mat','rectangles','colors','-v7');
 colors=parula(100);save('validation/matlab_parula.mat','colors','-v7');
 states=data.states;z=zeros(size(states,1),1);for k=1:size(n.AttractorTable,1),[~,ids]=ismember(n.AttractorTable{k,1},states,'rows');z(ids)=n.AttractorTable{k,3};end
 [x,y]=naiveMapping(states);rng(1);n.RandomIndicies=[randperm(size(states,1))';(size(states,1)+1:numel(x))'];
 opts=struct('plotTitle','Basin Size Landscape','showToolTip',0,'AnnotateAttractors',0,'selectedColorScheme','jet','mappingMethod','naive','plotTypes','BS','groupCyclicAttractors',0);
 [f,ok]=plot_AttractorLandscape(n,x,y,z,opts,states);assert(logical(ok));zlabel('Basin Sizes');print(f,'validation/matlab_basin.png','-dpng','-r120');permutation=n.RandomIndicies;save('validation/matlab_naive.mat','x','y','z','permutation','-v7');
catch e,disp(getReport(e));end
close all force;
