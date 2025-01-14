import numpy as np
import nibabel as nib
import copy
import glob
from brainspace.mesh.mesh_io import read_surface
from brainspace.plotting import plot_hemispheres, plot_surf, build_plotter
from brainspace.mesh import mesh_creation as mc


try:
    from hippunfold_toolbox import utils
except:
    import utils
from pathlib import Path

resourcesdir=str(Path(utils.__file__).parents[1]) + '/resources'


def surfplot_canonical_foldunfold(cdata, hemis=['L','R'], labels=['hipp','dentate'], den='0p5mm', tighten_cwindow=False, resourcesdir=resourcesdir, size=[350,230], **qwargs):
    '''
    Plots canonical folded and unfolded surfaces (hipp/dentate; folded/unfolded). This is good for cdata that isn't specific to one subject (eg. maybe it has been averaged across many subjects).
    
    cdata: array with the shape Vx2xF, where V is the number of vertices (including DG unless specified), 2 is the number of hemispheres (unless specified), and F is the number of rows/features
    kwargs: see hhttps://brainspace.readthedocs.io/en/latest/generated/brainspace.plotting.surface_plotting.plot_surf.html#brainspace.plotting.surface_plotting.plot_surf
    '''
    # load surfaces
    rh = read_surface(f'{resourcesdir}/canonical_surfs/tpl-avg_space-canonical_den-{den}_label-hipp_midthickness.surf.gii')
    ru = read_surface(f'{resourcesdir}/unfold_template_hipp/tpl-avg_space-unfold_den-{den}_midthickness.surf.gii')
    ru.Points = ru.Points[:,[1,0,2]] # reorient unfolded
    if len(labels)==2:
        ud = read_surface(f'{resourcesdir}/unfold_template_dentate/tpl-avg_space-unfold_den-{den}_midthickness.surf.gii')
        hd = read_surface(f'{resourcesdir}/canonical_surfs/tpl-avg_space-canonical_den-{den}_label-dentate_midthickness.surf.gii')
        ud.Points = ud.Points[:,[1,0,2]] # reorient unfolded
        ud.Points = ud.Points + [22, 0, 0] # translate unfolded dg
        # add to original
        npts = rh.n_points
        rh = mc.build_polydata(np.concatenate((rh.Points.copy(), hd.Points.copy())),
                                    cells=np.concatenate((rh.GetCells2D().copy(), hd.GetCells2D().copy()+npts)))
        ru = mc.build_polydata(np.concatenate((ru.Points.copy(), ud.Points.copy())),
                                cells=np.concatenate((ru.GetCells2D().copy(), ud.GetCells2D().copy()+npts)))
    # flip to get left hemisphere
    lh = mc.build_polydata(rh.Points.copy(), cells=rh.GetCells2D().copy())
    lh.Points[:,0] = -lh.Points[:,0]
    lu = mc.build_polydata(ru.Points.copy(), cells=ru.GetCells2D().copy())
    lu.Points[:,0] = -lu.Points[:,0]

    # do some cdata formatting
    cdata = np.reshape(cdata,[cdata.shape[0],len(hemis),-1])
    if tighten_cwindow>0: 
        for i in range(0,cdata.shape[2]):
            cdata[:,:,i] = utils.bound_cdata(cdata[:,:,i])
    size[0] = size[0]*len(hemis)
    size[1] = size[1]*cdata.shape[2]

    # set up layout
    surfDict = {'Lf':lh, 'Lu':lu, 'Rf':rh, 'Ru':ru}
    surfList = np.ones((cdata.shape[2],len(hemis)*2),dtype=object)
    arrName = np.ones((cdata.shape[2],len(hemis)*2),dtype=object)
    for h,hemi in enumerate(hemis):
        if hemi=='L':
            surfList[:,[h,h+1]] = np.array([f"{hemi}f",f"{hemi}u"])
            for f in range(cdata.shape[2]):
                lh.append_array(cdata[:,h,f], name=f'feature{f}', at='point')
                lu.append_array(cdata[:,h,f], name=f'feature{f}', at='point')
        elif hemi=='R':
            surfList[:,[h*2,h*2 +1]] = np.array([f"{hemi}u",f"{hemi}f"])
            for f in range(cdata.shape[2]):
                rh.append_array(cdata[:,h,f], name=f'feature{f}', at='point')
                ru.append_array(cdata[:,h,f], name=f'feature{f}', at='point')
        for f in range(cdata.shape[2]):
            arrName[f,:] = f'feature{f}'

    new_qwargs = dict(zoom=1.5, nan_color=(0,0,0,0))
    new_qwargs.update(qwargs)
    p = plot_surf(surfDict,surfList, array_name=arrName, size=size, **new_qwargs)
    return p


def surfplot_sub_foldunfold(hippunfold_dir, sub, ses, features, hemis=['L','R'], labels=['hipp','dentate'], den='0p5mm', modality='T1w', tighten_cwindow=True, rotate=True,  resourcesdir=resourcesdir, size=[400,200], cmap='viridis', **qwargs):
    '''
    Plots subject-specific folded and unfolded surfaces (hipp/dentate; folded/unfolded). 
    
    Inputs are path/filenames (eg. sub='01', ses='01') 
        if ses doesn't exist, simply set it to ''. 
    features: list of strings. Can include 'thickness', 'curvature', 'gyrification', 'subfields', or any added data that follows the same naming convention
    kwargs: see hhttps://brainspace.readthedocs.io/en/latest/generated/brainspace.plotting.surface_plotting.plot_surf.html#brainspace.plotting.surface_plotting.plot_surf
    '''

    if len(ses)>0: 
        ses = 'ses-'+ses
        uses = '_'+ses 
    else: 
        uses = ''
    size[0] = size[0]*len(hemis)
    size[1] = size[1]*len(features)

    # load surfaces
    surf = []
    n=0
    for hemi in hemis:
        for space in [modality,'unfold']:
            for label in labels:
                fn1 = f'{hippunfold_dir}/sub-{sub}/{ses}/surf/sub-{sub}{uses}_hemi-{hemi}_space-{space}_den-{den}_label-{label}_midthickness.surf.gii'
                try:
                    s = read_surface(fn1)
                    if label=='hipp':
                        nptsHipp = s.n_points
                    if space=='unfold':
                        s.Points = s.Points[:,[1,0,2]] # reorient unfold
                        if label=='dentate':
                            s.Points = s.Points + [22,0,0] # translate DG
                    if label=='dentate': # concatenate dentate to hipp
                        s = mc.build_polydata(np.concatenate((oldsurf.Points.copy(), s.Points.copy())),
                                        cells=np.concatenate((oldsurf.GetCells2D().copy(), s.GetCells2D().copy()+nptsHipp)))
                        if hemi=="L" and space=='unfold': # flip L unfolded
                            s.Points[:,0] = -s.Points[:,0]
                    oldsurf = s
                except:
                    print(fn1 + ' failed')
            surf.append(s)
    npts = len(surf[0].Points)

    # rotate surfaces to approx coronal-oblique
    if rotate:
        aff = np.loadtxt(f'{resourcesdir}/xfms/corobl-20deg_xfm.txt')
        for i,h in enumerate(hemis):
            p = np.hstack((surf[i*2].Points, np.ones((npts,1))))
            p = p @ aff
            surf[i*2].Points = p[:,:3]

    # load features data
    ind = [range(nptsHipp), range(nptsHipp,npts)]
    cdata = np.ones([npts,len(hemis),len(features)]) * np.nan
    for h,hemi in enumerate(hemis):
        for l,label in enumerate(labels):
            for f,feature in enumerate(features):
                if feature=='subfields': 
                    type='label'
                else:
                    type='shape'
                fn2 = f'{hippunfold_dir}/sub-{sub}/{ses}/surf/sub-{sub}{uses}_hemi-{hemi}_space-{modality}_den-{den}_label-{label}_*{feature}*.{type}.gii'
                fn3 = glob.glob(fn2)
                try:
                    cdata[ind[l],h,f]= nib.load(fn3[0]).darrays[0].data
                except:
                    print(fn2 + ' failed')

    # options
    cmaps = np.ones((len(features),len(hemis)*2),dtype=object)
    cmaps[:] = cmap
    for f,feature in enumerate(features):
        if feature=='subfields':
            cdata[ind[1],:,f] = np.nanmax(cdata)+1
            cmaps[f,:] = ('tab10')
        else:
            if tighten_cwindow>0: 
                cdata[:,:,f] = utils.bound_cdata(cdata[:,:,f])

    # set up layout
    surfDict = {}
    surfList = np.ones((len(features),len(hemis)*2),dtype=object)
    arrName = np.ones((len(features),len(hemis)*2),dtype=object)
    for h,hemi in enumerate(hemis):
        surfDict.update({f"{hemi}f":surf[h*2]})
        surfDict.update({f"{hemi}u":surf[h*2 +1]})
        if hemi=='L':
            surfList[:,[h,h+1]] = np.array([f"{hemi}f",f"{hemi}u"])
        elif hemi=='R':
            surfList[:,[h*2,h*2 +1]] = np.array([f"{hemi}u",f"{hemi}f"])
        for f,feature in enumerate(features):
            surf[h*2].append_array(cdata[:,h,f], name=feature, at='point')
            surf[h*2 +1].append_array(cdata[:,h,f], name=feature, at='point')
            arrName[f,:] = feature

    p = plot_surf(surfDict,surfList, array_name=arrName, nan_color=(0,0,0,0), size=size, cmap=cmaps, **qwargs)
    return p

