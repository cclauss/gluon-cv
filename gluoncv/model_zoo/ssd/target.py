"""SSD training target generator."""
from __future__ import absolute_import

from mxnet import nd
from mxnet.gluon import Block
from ..matchers import CompositeMatcher, BipartiteMatcher, MaximumMatcher
from ..samplers import OHEMSampler
from ..coders import MultiClassEncoder, NormalizedBoxCenterEncoder
from ..bbox import BBoxCenterToCorner


class SSDTargetGenerator(Block):
    """Training targets generator for Single-shot Object Detection.

    Parameters
    ----------
    iou_thresh : float
        IOU overlap threshold for maximum matching, default is 0.5.
    neg_thresh : float
        IOU overlap threshold for negative mining, default is 0.5.
    negative_mining_ratio : float
        Ratio of hard vs positive for negative mining.
    stds : array-like of size 4, default is (0.1, 0.1, 0.2, 0.2)
        Std value to be divided from encoded values.
    """
    def __init__(self, iou_thresh=0.5, neg_thresh=0.5, negative_mining_ratio=3,
                 stds=(0.1, 0.1, 0.2, 0.2), **kwargs):
        super(SSDTargetGenerator, self).__init__(**kwargs)
        self._matcher = CompositeMatcher([BipartiteMatcher(), MaximumMatcher(iou_thresh)])
        self._sampler = OHEMSampler(negative_mining_ratio, thresh=neg_thresh)
        self._cls_encoder = MultiClassEncoder()
        self._box_encoder = NormalizedBoxCenterEncoder(stds=stds)
        self._center_to_corner = BBoxCenterToCorner(split=False)

    # pylint: disable=arguments-differ
    def forward(self, anchors, cls_preds, gt_boxes, gt_ids):
        anchors = self._center_to_corner(anchors.reshape((-1, 4)))
        ious = nd.transpose(nd.contrib.box_iou(anchors, gt_boxes), (1, 0, 2))
        matches = self._matcher(ious)
        samples = self._sampler(matches, cls_preds, ious)
        cls_targets = self._cls_encoder(samples, matches, gt_ids)
        box_targets, box_masks = self._box_encoder(samples, matches, anchors, gt_boxes)
        return cls_targets, box_targets, box_masks
