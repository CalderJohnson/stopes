# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import logging
import typing as tp
from dataclasses import dataclass, field
from pathlib import Path

import hydra
import numpy as np
from omegaconf import MISSING

import stopes.core.utils as stutils
from stopes.core.stopes_module import Requirements, StopesModule

from .utils import (
    Audio,
    IntersectMethods,
    MiningLineResult,
    compute_overlap,
    split_mining_line,
)

log = logging.getLogger("stopes.speech.postprocess_audio")


@dataclass
class PostProcessAudioConfig:
    """
    output_dir: path to the output directory
    output_filename: name for the file to create
    mining_result_path: path to the mining result
        (.tsv or .gz)
    min_audio_length: minimal length to keep a sample
        (in ms)
    mining_threshold: minimal value to keep a pair
        (audio/text or audio/audio)
    max_overlap (float): maximal admissible value between
        two pairs. Lowest score is discarded.
    overlap_method (IntersectMethods): see IntersectMethods
    sampling_factor (int, optional): see Audio
    requirements (Requirements): required hardware to run
        on cluster
    """

    output_dir: Path = MISSING
    output_filename: str = MISSING
    mining_result_path: Path = MISSING  # path to .gz
    min_audio_length: int = MISSING  # length in ms
    mining_threshold: float = MISSING  # min score
    max_overlap: float = 0.2  # max admissible overlap see
    # IntersectMethods for how the overlap is computed
    overlap_method: IntersectMethods = IntersectMethods.FRACTION
    sampling_factor: tp.Union[int, None] = None
    requirements: Requirements = field(
        default=Requirements(
            nodes=1,
            tasks_per_node=1,
            gpus_per_node=0,
            cpus_per_task=1,
            timeout_min=600,
        )
    )


StatsDict = tp.Dict[str, tp.Dict[str, int]]


class PostProcessAudioModule(StopesModule):
    config: PostProcessAudioConfig

    def __init__(self, config: PostProcessAudioConfig):
        super().__init__(config, PostProcessAudioConfig)
        self.output_dir = Path(self.config.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.src_attr = "src"
        self.file_lines = 0
        self.mining_threshold = self.config.mining_threshold
        self.min_audio_length = self.config.min_audio_length

    def requirements(self) -> Requirements:
        return self.config.requirements

    def load_input(self, mining_result: MiningLineResult) -> Audio:
        return getattr(mining_result, self.src_attr)

    @staticmethod
    def which_object_audio(src: tp.Any, tgt: tp.Any, line: str) -> str:
        if isinstance(src, Audio):
            return "src"
        if isinstance(tgt, Audio):
            return "tgt"

        raise ValueError(
            "At least one item needs to be an audio sample. Received: "
            f"{type(src)} / {type(tgt)}\nInput: {line}"
        )

    def load_file(self) -> tp.Dict[str, tp.List[MiningLineResult]]:
        log.info("Loading file...")
        sources: tp.Dict[str, tp.List[MiningLineResult]] = {}
        passing_filters = 0
        with stutils.open(self.config.mining_result_path) as f:
            line = f.readline()
            if not line:
                raise ValueError(f"File {self.config.mining_result_path} is empty.")
            self.file_lines += 1
            # check that one of the the two items is audio
            mining_result = split_mining_line(
                line,
                sampling_factor=self.config.sampling_factor,
            )
            self.src_attr = self.which_object_audio(
                mining_result.src, mining_result.tgt, line
            )

            while line:
                self.file_lines += 1
                mining_result = split_mining_line(line)
                path = self.load_input(mining_result).path
                if self.line_passes_thresholds(mining_result):
                    passing_filters += 1
                    if path in sources.keys():
                        sources[path].append(mining_result)
                    else:
                        sources[path] = [mining_result]
                line = f.readline()
        log.info(
            f"Passing filters (audio length & score): {passing_filters} / {self.file_lines}"
        )
        return sources

    def line_passes_thresholds(self, line: MiningLineResult) -> bool:
        return (
            line.score > self.mining_threshold
            and self.load_input(line).duration > self.min_audio_length
        )

    def postprocess(
        self, sources: tp.Dict[str, tp.List[MiningLineResult]]
    ) -> tp.Tuple[tp.List[MiningLineResult], StatsDict]:
        valid_audio: tp.List[MiningLineResult] = []
        filtering_stats: StatsDict = {}
        for i, (path, line_list) in enumerate(sources.items()):
            if i % 1000 == 0:
                log.info(f"{i}/{len(sources)}")
            # filters on score and duration already applied at
            # loading to reduce size on kept input

            # sort on start of object 1 to reduce complexity
            line_list = sorted(
                line_list,
                key=lambda x: self.load_input(x).start,
            )
            kept_lines: tp.List[MiningLineResult] = []
            # since we have sorted by start
            # for a sequence:
            # if start A < start B < start C
            # if A & C and A & B overlap but not B & C
            # that means that B is included in A
            # so B will not be kept (example:
            # |-AAAAAAAAAAAAA--|
            # |---BBB----------|
            # |----------CCCCCC|
            # )
            # As a result we only need to check
            # if the overlap is higher than threshold
            # for the last kept element
            # TODO handle case: A, B, C
            # score A > score B
            # score C > score A
            # Time order:
            # |-AAAAAAAAAAAA---|
            # |---BBB----------|
            # |---------CCCCCCC|
            # Score order:
            # |---------CCCCCCC|
            # |-AAAAAAAAAAAA---|
            # |---BBB----------|
            # ==> B & C should be kept
            # With a score-ordered heuristice
            # A is skipped due to C

            for line in line_list:
                if len(kept_lines) == 0:
                    kept_lines.append(line)
                else:
                    overlap = self.compute_overlap(
                        self.load_input(kept_lines[-1]),
                        self.load_input(line),
                    )
                    if overlap > self.config.max_overlap:
                        if kept_lines[-1].score < line.score:
                            kept_lines[-1] = line
                    else:
                        kept_lines.append(line)
            # TODO: experiment to see if running the filtering step
            # on the second audio object (if file is audio/audio)
            # has a significant effect on output
            valid_audio = valid_audio + kept_lines
            filtering_stats[path] = {
                "starting_lines": len(line_list),
                "kept_lines": len(kept_lines),
            }
        return valid_audio, filtering_stats

    def compute_overlap(self, audio1: Audio, audio2: Audio) -> float:
        return compute_overlap(
            segment1=audio1, segment2=audio2, method=self.config.overlap_method
        )

    def save_results(self, valid_lines) -> Path:
        out_path = self.config.output_dir / self.config.output_filename
        log.info(f"saving results to: {out_path}")
        with stutils.open(out_path, "w") as f:
            for mining_result in valid_lines:
                # TODO: [sampling_factor] we assume the audio is
                # sampled at 16kHz and timestamps correspond
                # to wav cycles or ms
                part1 = str(mining_result.src)
                part2 = str(mining_result.tgt)
                print(str(mining_result.score), part1, part2, sep="\t", file=f)
        log.info(f"saved {len(valid_lines)} lines / starting with: {self.file_lines}")
        return out_path

    def run(
        self, iteration_value: tp.Optional[tp.Any] = None, iteration_index: int = 0
    ) -> Path:
        sources = self.load_file()
        valid_lines, filtering_stats = self.postprocess(sources)
        # TODO: save results in a streaming fashion like in other modules.
        outfile = self.save_results(valid_lines)

        paths = [p for p in filtering_stats.keys()]
        percentage_kept = np.array(
            [
                float(filtering_stats[p]["kept_lines"])
                / filtering_stats[p]["starting_lines"]
                for p in paths
            ]
        )
        avg, std = np.mean(percentage_kept), np.std(percentage_kept)
        log.info(f"Percentage of samples kept by audio file: {avg} +/- {std}")
        sigmas = 3
        below_sigs = [
            paths[int(i)]
            for i in np.argwhere(percentage_kept < avg - sigmas * std).squeeze()
        ]
        if below_sigs:
            log.warning(
                f"Found {len(below_sigs)} files with abnormally low kept samples (<{sigmas}sigma): {below_sigs[:50]}"
            )

        total_src_time = 0.0
        for valid in valid_lines:
            total_src_time += self.load_input(valid).duration
        log.info(f"{total_src_time/(1000*3600)} hours of audio remaining for source")

        return outfile


@hydra.main(
    config_path="../../pipelines/tests/conf/fb_preset",
    config_name="postprocess_audio",
    version_base=None,
)
def main(config: PostProcessAudioConfig) -> Path:
    postprocess = PostProcessAudioModule(config=config)
    return postprocess.run()


if __name__ == "__main__":
    main()
