![stopes](/website/static/img/banner.png?raw=true "stopes by NLLB.")


# `stopes`: A library for preparing data for machine translation research

As part of the FAIR No Language Left Behind (NLLB) ([Paper](https://research.facebook.com/publications/no-language-left-behind/), [Website](https://ai.facebook.com/research/no-language-left-behind/), [Blog](https://ai.facebook.com/blog/nllb-200-high-quality-machine-translation/))
project to drive inclusion through machine translation, a large amount of data was processed to create training data. We provide the libraries and tools we used to:

1. create clean monolingual data from web data
2. mine bitext
3. easily write scalable pipelines for processing data for machine translation

Full documentation on https://facebookresearch.github.io/stopes

## Examples

checkout the `demo` directory for an example usage with the [WMT22 Shared Task: Large-Scale Machine Translation Evaluation for African
Languages](https://statmt.org/wmt22/large-scale-multilingual-translation-task.html) data.

## Requirements

`stopes` relies on:

- submitit to schedule jobs when ran on clusters
- hydra-core version >= 1.2.0 for configuration
- fairseq to use LASER encoders
- PyTorch version >= 1.5.0
- Python version >= 3.8

## Installing stopes

stopes uses [flit](https://flit.pypa.io/) to manage its setup, you will need a recent version of
pip for the install to work. We recommend that you first upgrade pip:
`python -m pip install --upgrade pip`

The mining pipeline relies on fairseq to run LASER encoders, because of competing dependency version, you'll have to first install fairseq with pip separately:

```
pip install fairseq==0.12.2
```

You can then install stopes with pip:

```
git clone https://github.com/facebookresearch/stopes.git
cd stopes
pip install -e '.[dev,mono,mining]'
```

You can choose what to install. If you are only interested in `mining`, you do not need to install `dev`, and `mono`. If you are interested in the distillation pipeline, you will need to install at least `mono`. `mining` will install the cpu version of the dependencies for mining, if you want to do mining on gpu, and your system is compatible, you can install `[mining,mining-gpu]`.

Currently `fairseq` and `stopes` require different version of hydra, so `pip` might output some warnings, do not worry about them, we want hydra>=1.1.

If you plan to train a lot of NMT model you will also want to setup apex to get a faster training.

```
git clone https://github.com/NVIDIA/apex
cd apex
pip install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" \
  --global-option="--deprecated_fused_adam" --global-option="--xentropy" \
  --global-option="--fast_multihead_attn" ./
```

### Speech package installing

Some speech packages like the MMS Text-to-Speech(TTS) require additional library installation, see [here](stopes/speech/README.md) for more details.

## How `stopes` works

`stopes` is made of a few different parts:

1. `core` provides a library to write readable piplines
2. `modules` provides a set of modules using the core library and implementing
   common steps in our mining and evaluation pipelines
3. `pipelines` provides pipeline implementation for the data pipelines we use in
   NLLB:

- `monolingual` to preprocess and clean single language data
- `bitext` to run the "global mining" pipeline and extract aligned sentences
  from two monolingual datasets. (inspired by
  [CCMatrix](https://ai.facebook.com/blog/ccmatrix-a-billion-scale-bitext-data-set-for-training-translation-models/))
- `distilation` to run our sequence-level knowledge distillation pipeline which trains a small student model from a pre-trained large teacher model (approach based on https://arxiv.org/abs/1606.07947)

4. `eval` provides a set of evaluation tools, including ALTI+ and BLASER for text-free speech translation evaluation.
5. `demo` contains applications of stopes, including a quickstart demo that you can run at home of mining as well as a example usage of ALTI+ for toxicity and hallucination analysis.

**Full documentation**: see https://facebookresearch.github.io/stopes
or the `websites/docs` folder.

## Contributing

See the [CONTRIBUTING](CONTRIBUTING.md) file for how to help out.

## Contributors

You can find the list of the main contributors in the [NLLB](https://github.com/facebookresearch/fairseq/tree/nllb) and [Seamless Communication](https://github.com/facebookresearch/seamless_communication) papers.

(in alphabetical order)

## Citation

If you use `stopes` in your work, please cite:

```bibtex
@inproceedings{andrews-etal-2022-stopes,
    title = "stopes - Modular Machine Translation Pipelines",
    author = "Pierre Andrews, Guillaume Wenzek, Kevin Heffernan, Onur Çelebi, Anna Sun, Ammar Kamran, Yingzhe Guo, Alexandre Mourachko, Holger Schwenk, Angela Fan",
    booktitle = "Proceedings of the 2022 Conference on Empirical Methods in Natural Language Processing: System Demonstrations",
    month = dec,
    year = "2022",
    publisher = "Association for Computational Linguistics",
}
```

Some of the tools in stopes, like BLASER and ALTI have their own publications, please see in the specific readme for the correct citation to use for these specific tools.

`stopes` was originally built as part of the NLLB project, if you use any models/datasets/artifacts published in NLLB, please cite :

```bibtex
@article{nllb2022,
  title={No Language Left Behind: Scaling Human-Centered Machine Translation},
  author={{NLLB Team} and Costa-jussà, Marta R. and Cross, James and Çelebi, Onur and Elbayad, Maha and Heafield, Kenneth and Heffernan, Kevin and Kalbassi, Elahe and Lam, Janice and Licht, Daniel and Maillard, Jean and Sun, Anna and Wang, Skyler and Wenzek, Guillaume and Youngblood, Al and Akula, Bapi and Barrault, Loic and Mejia-Gonzalez, Gabriel and Hansanti, Prangthip and Hoffman, John and Jarrett, Semarley and Sadagopan, Kaushik Ram and Rowe, Dirk and Spruit, Shannon and Tran, Chau and Andrews, Pierre and Ayan, Necip Fazil and Bhosale, Shruti and Edunov, Sergey and Fan, Angela and Gao, Cynthia and Goswami, Vedanuj and Guzmán, Francisco and Koehn, Philipp and Mourachko, Alexandre and Ropers, Christophe and Saleem, Safiyyah and Schwenk, Holger and Wang, Jeff},
  year={2022}
}
```

If you use SeamlessM4T in your work or any models/datasets/artifacts published in SeamlessM4T, please cite :

```bibtex
@article{seamlessm4t2023,
  title={SeamlessM4T—Massively Multilingual \& Multimodal Machine Translation},
  author={{Seamless Communication}, Lo\"{i}c Barrault, Yu-An Chung, Mariano Cora Meglioli, David Dale, Ning Dong, Paul-Ambroise Duquenne, Hady Elsahar, Hongyu Gong, Kevin Heffernan, John Hoffman, Christopher Klaiber, Pengwei Li, Daniel Licht, Jean Maillard, Alice Rakotoarison, Kaushik Ram Sadagopan, Guillaume Wenzek, Ethan Ye,  Bapi Akula, Peng-Jen Chen, Naji El Hachem, Brian Ellis, Gabriel Mejia Gonzalez, Justin Haaheim, Prangthip Hansanti, Russ Howes, Bernie Huang, Min-Jae Hwang, Hirofumi Inaguma, Somya Jain, Elahe Kalbassi, Amanda Kallet, Ilia Kulikov, Janice Lam, Daniel Li, Xutai Ma, Ruslan Mavlyutov, Benjamin Peloquin, Mohamed Ramadan, Abinesh Ramakrishnan, Anna Sun, Kevin Tran, Tuan Tran, Igor Tufanov, Vish Vogeti, Carleigh Wood, Yilin Yang, Bokai Yu, Pierre Andrews, Can Balioglu, Marta R. Costa-juss\`{a} \footnotemark[3], Onur \,{C}elebi,Maha Elbayad,Cynthia Gao, Francisco Guzm\'an, Justine Kao, Ann Lee, Alexandre Mourachko, Juan Pino, Sravya Popuri, Christophe Ropers, Safiyyah Saleem, Holger Schwenk, Paden Tomasello, Changhan Wang, Jeff Wang, Skyler Wang},
  journal={ArXiv},
  year={2023}
}
```

## License

`stopes` is MIT licensed, as found in the LICENSE file.

When using speech mining with the [SONAR](https://github.com/facebookresearch/SONAR) models, beware that this code and models are released under [CC-BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
