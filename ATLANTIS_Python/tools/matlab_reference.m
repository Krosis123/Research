cd(fileparts(fileparts(mfilename('fullpath'))));
root=fullfile(pwd,'original','ATLANTIS','Toolbox'); if ~exist(root,'dir'), root=fullfile(pwd,'reference','Toolbox'); end; addpath(genpath(root));
set(0,'DefaultFigureVisible','off');
out=fullfile(pwd,'validation');
try
 n=NetworkDataStructure; n.NetworkType='WeightsBased';
 p=fullfile(pwd,'examples','Case Study 1','Input Files');
 assert(logical(parse_NetworkFile(n,'NetworkFile.csv',p)));
 generate_StatesCombinations(n); n.AttractorSearchDuration=200;
 assert(logical(deterministicEngine_WeightsBased(n,1)));
 nodeNames=n.NodeNames; weights=n.EdgeWeights; basal=n.BasalValues; states=n.NetworkStateList; attractorTable=n.AttractorTable;
 save(fullfile(out,'matlab_yeast_deterministic.mat'),'nodeNames','weights','basal','states','attractorTable','-v7');
 [ok,raw]=parse_CellFateLogic(n,'Cell Fate Determination Logic.csv',p); assert(logical(ok)); assert(logical(classify_Attractors(n)));
 attractorTable=n.AttractorTable; cellFateLandscape=n.CellFateLandscape;
 save(fullfile(out,'matlab_yeast_fates.mat'),'attractorTable','cellFateLandscape','-v7');
 n.Noise=5; n.DegradationConstant=.001; n.TimeSteps=200; n.ErrorThreshold=1e-7; n.PruneStateSpace=1;
 assert(logical(find_StateTransitionProbabilities(n,1))); assert(logical(find_SteadyStateProbabilities(n,1)));
 states=n.PrunnedStateSpacePA; transition=n.StateTransitionProbabilities; probabilities=n.SteadyStateProbabilities; iteration=n.SteadyStateTimeStep;
 save(fullfile(out,'matlab_yeast_probabilistic.mat'),'states','transition','probabilities','iteration','-v7');
 r=NetworkDataStructure; r.NetworkType='RulesBased'; r.NodeNames={'A','B'}; r.NodeCount=2;
 r.SourceNodeIndices={1;2}; r.TargetNodeIndices={1;2}; r.NodeUpdateLogic={[1;0];[0;1]};
 r.NetworkStateList=[0 0;0 1;1 0;1 1]; r.AttractorSearchDuration=200;
 assert(logical(deterministicEngine_RulesBased(r,1))); attractorTable=r.AttractorTable;
 save(fullfile(out,'matlab_rules_deterministic.mat'),'attractorTable','-v7');
 x=[0 0 0;0 0 1;0 1 0;1 0 0;1 1 1]; [xy,stress]=sammonMapping(x);
 save(fullfile(out,'matlab_sammon.mat'),'x','xy','stress','-v7');
 fid=fopen(fullfile(out,'matlab_reference_success.txt'),'w');fprintf(fid,'MATLAB %s\nAll reference runs completed\n',version);fclose(fid);
catch e
 disp(getReport(e)); fid=fopen(fullfile(out,'matlab_reference_error.txt'),'w');fprintf(fid,'%s',getReport(e));fclose(fid);
end
close all force;

