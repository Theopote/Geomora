from __future__ import annotations

import cv2
import numpy as np


def load_gray(image_path: str) -> np.ndarray:
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def detect_and_match(primary_gray: np.ndarray, secondary_gray: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    detector = cv2.ORB_create(5000)
    keypoints_a, descriptors_a = detector.detectAndCompute(primary_gray, None)
    keypoints_b, descriptors_b = detector.detectAndCompute(secondary_gray, None)

    if descriptors_a is None or descriptors_b is None:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), 0

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = matcher.match(descriptors_a, descriptors_b)
    if not matches:
        return np.empty((0, 2), dtype=np.float32), np.empty((0, 2), dtype=np.float32), 0

    matches = sorted(matches, key=lambda item: item.distance)
    points_a = np.float32([keypoints_a[m.queryIdx].pt for m in matches])
    points_b = np.float32([keypoints_b[m.trainIdx].pt for m in matches])
    return points_a, points_b, len(matches)


def estimate_planar_homography(
    points_primary: np.ndarray,
    points_secondary: np.ndarray,
) -> tuple[np.ndarray | None, int]:
    if len(points_primary) < 4 or len(points_secondary) < 4:
        return None, 0

    homography, mask = cv2.findHomography(
        points_secondary,
        points_primary,
        cv2.RANSAC,
        5.0,
    )
    if homography is None or mask is None:
        return None, 0

    inliers = int(mask.ravel().sum())
    return homography, inliers


def homography_confidence(match_count: int, inlier_count: int) -> float:
    if match_count <= 0:
        return 0.0
    ratio = inlier_count / match_count
    volume_factor = min(1.0, inlier_count / 40.0)
    return round(min(0.98, 0.25 + ratio * 0.55 + volume_factor * 0.18), 4)
