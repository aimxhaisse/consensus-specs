from copy import deepcopy

from eth2spec.test.helpers.keys import privkeys
from eth2spec.utils.bls import (
    bls_sign,
    only_with_bls,
)
from eth2spec.utils.ssz.ssz_impl import (
    signing_root,
)

from .attestations import (
    sign_shard_attestation,
)


@only_with_bls()
def sign_shard_block(spec, beacon_state, shard_state, block, proposer_index=None):
    if proposer_index is None:
        proposer_index = spec.get_shard_proposer_index(beacon_state, shard_state.shard, block.slot)

    privkey = privkeys[proposer_index]

    block.signature = bls_sign(
        message_hash=signing_root(block),
        privkey=privkey,
        domain=spec.get_domain(
            beacon_state,
            spec.DOMAIN_SHARD_PROPOSER,
            spec.compute_epoch_of_shard_slot(block.slot),
        )
    )


def build_empty_shard_block(spec,
                            beacon_state,
                            shard_state,
                            slot,
                            signed=False,
                            full_attestation=False):
    if slot is None:
        slot = shard_state.slot

    parent_epoch = spec.compute_epoch_of_shard_slot(shard_state.latest_block_header.slot)
    if parent_epoch * spec.SLOTS_PER_EPOCH == beacon_state.slot:
        beacon_block_root = spec.signing_root(beacon_state.latest_block_header)
    else:
        beacon_block_root = spec.get_block_root(beacon_state, parent_epoch)

    previous_block_header = deepcopy(shard_state.latest_block_header)
    if previous_block_header.state_root == spec.Hash():
        previous_block_header.state_root = shard_state.hash_tree_root()
    parent_root = signing_root(previous_block_header)

    block = spec.ShardBlock(
        shard=shard_state.shard,
        slot=slot,
        beacon_block_root=beacon_block_root,
        parent_root=parent_root,
        block_size_sum=shard_state.block_size_sum + spec.SHARD_HEADER_SIZE,
    )

    if full_attestation:
        shard_committee = spec.get_shard_committee(beacon_state, shard_state.shard, block.slot)
        block.aggregation_bits = list(
            (True,) * len(shard_committee) +
            (False,) * (spec.MAX_PERIOD_COMMITTEE_SIZE * 2 - len(shard_committee))
        )
        block.attestations = sign_shard_attestation(
            spec,
            beacon_state,
            shard_state,
            block,
            participants=shard_committee,
        )

    if signed:
        sign_shard_block(spec, beacon_state, shard_state, block)

    return block
