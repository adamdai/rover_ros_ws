"""LiDAR utils

"""

import numpy as np
import open3d as o3d


def dist_filter(P, threshold):
    """Filter points by distance
    
    Parameters
    ----------
    P : np.array (n_pts x 3)
        Point cloud to filter

    Parameters
    ----------
    np.array (n_pts_filtered x 3)
        Filtered point cloud
    
    """
    dists = np.linalg.norm(P, axis=1)
    keep_idx = dists < threshold
    return P[keep_idx,:] 


def bounds_mask(P_2D, width=0.5):
    """Given 2D (axis-aligned) point cloud, find mask of points belonging to boundaries
    
    Parameters
    ---------
    P_2D : np.array (n_pts x 2)
        2D point cloud
    width : float
        Bounds width
    
    Returns
    -------
    mask : bool np.array (n_pts)
        Mask for indices of boundary points

    """
    mask = np.zeros(len(P_2D), dtype=bool)

    # x-dim walls
    x_max = np.max(P_2D[:,0])
    mask = mask | ((P_2D[:,0] <= x_max + width) & (P_2D[:,0] >= x_max - width))
    x_min = np.min(P_2D[:,0])
    mask = mask | ((P_2D[:,0] <= x_min + width) & (P_2D[:,0] >= x_min - width))

    # y-dim walls
    y_max = np.max(P_2D[:,1])
    mask = mask | ((P_2D[:,1] <= y_max + width) & (P_2D[:,1] >= y_max - width))
    y_min = np.min(P_2D[:,1])
    mask = mask | ((P_2D[:,1] <= y_min + width) & (P_2D[:,1] >= y_min - width))

    return mask


def rotate_points(P, theta):
    """Rotate 2D points by theta

    Parameters
    ----------
    P : np.array (n_pts x 2)
        2D points
    theta : float
        Angle to rotate in radians
    
    """
    R = np.array([[np.cos(theta), -np.sin(theta)],
                  [np.sin(theta), np.cos(theta)]])
    return (R @ P.T).T


def detect_landmark(P, x_hat, d_thresh=6.0, lidar_height=0.15):
    """Detect landmark

    Given point cloud and state estimate, detect landmark position in robot local frame.
    
    Parameters
    ----------
    P : np.array (n_pts x 3)
        3D point cloud
    x_hat : np.array (4 x 1)
        State estimate (x, y, theta, v)
    
    Returns
    -------
    np.array (3)
        Estimated 3D landmark position in local frame
    
    """
    # Distance filter  NOTE: may not be needed anymore
    P = dist_filter(P, d_thresh)
    # Ground removal
    P = P[P[:,2] > -lidar_height,:] 
    # Transform to global frame in 2D
    P_2D = P[:,:2]
    P_2D_global = rotate_points(P_2D, x_hat[2])
    P_2D_global = P_2D_global + x_hat[:2]
    # Use search region to extract landmark in global frame
    mask = np.ones(len(P), dtype=bool)
    mask = mask & ((P_2D_global[:,0] <= LM_BOX_XMAX) & (P_2D_global[:,0] >= LM_BOX_XMIN))
    mask = mask & ((P_2D_global[:,1] <= LM_BOX_YMAX) & (P_2D_global[:,1] >= LM_BOX_YMIN))

    landmark_pts = P[mask]
    return np.mean(landmark_pts, axis=0)


def extract_landmarks(P, d_thresh=6.0, lidar_height=0.15, dbscan_eps=0.2, dbscan_minpts=10):
    """Extract landmark positions from point cloud

    Parameters
    ----------
    P : np.array (n_pts x 3)
        3D point cloud
    d_thresh : float (meters)
        Distance threshold for filtering
    lidar_height : float (meters)
        LiDAR height (for ground plane removal)

    Returns
    -------
    
    """
    # Distance filter
    P_filter = dist_filter(P, d_thresh)
    # Ground removal
    P_filter = P_filter[P_filter[:,2] > -lidar_height,:] 
    # DBSCAN clustering
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(P_filter)
    labels = np.array(pcd.cluster_dbscan(eps=dbscan_eps, min_points=dbscan_minpts))
    clusters = [[] for _ in range(labels.max()+1)]  # TODO: faster way to do this?
    for i in range(len(labels)):
        if labels[i] >= 0:
            clusters[labels[i]].append(i)


def spherical_project(P):
    """Project 3D point cloud to 2D using spherical projection

    Parameters
    ----------
    P : np.array (n_pts x 3)
        3D point cloud
    
    Returns
    -------
    thetas : np.array (n_pts)
        Azimuth angles
    phis : np.array (n_pts)
        Elevation angles

    """
    thetas = np.arctan2(P[:,1], P[:,0])
    Rxy = np.sqrt(P[:,0]**2 + P[:,1]**2)
    phis = np.arctan2(P[:,2], Rxy)
    return thetas, phis