import io, os, sys
import pandas as pd
import numpy as np
import re
import modelling
import tokenization
import tensorflow as tf
import emoji
from ekphrasis.classes.preprocessor import TextPreProcessor
import wordsegment


def tensorize(input_tensor, type):
    return tf.convert_to_tensor(input_tensor, type)


def tokenize(sents, max_seq_len):
    """Tokenize the data sent by sent into Bert sub-tokens. Append input masks"""
    bert_tokenizer = tokenization.FullTokenizer(vocab_file="cased_L-12_H-768_A-12/vocab.txt", do_lower_case=True)
    input_ids = []
    input_mask = []
    examples = []
    for sent in sents:
        """Error may be occured due to non-unicode text (emoji)"""
        sent_tokenized = bert_tokenizer.tokenize(sent)
        example = ["[CLS]"] + sent_tokenized + ["[SEP]"]
        sent_input_ids = bert_tokenizer.convert_tokens_to_ids(example)
        sent_input_mask = [1] * len(example)
        for _ in range(len(example), max_seq_len):
            sent_input_ids.append(0)
            sent_input_mask.append(0)
        input_ids.append(sent_input_ids[:max_seq_len])
        input_mask.append(sent_input_mask[:max_seq_len])
        examples.append(example[:max_seq_len])
        assert len(sent_input_ids) == len(sent_input_mask)

    input_ids = np.array(input_ids)
    input_mask = np.array(input_mask)

    return tensorize(input_ids, tf.int32), tensorize(input_mask, tf.int32), examples


def bert_transformer(input_ids, input_mask, bert_config, config):
    bert_model = modelling.BertModel(
        config=bert_config,
        is_training=config['do_train'],
        input_ids=input_ids,
        input_mask=input_mask,
        use_one_hot_embeddings=False,
        scope='bert')
    bert_encoder_layer = bert_model.get_sequence_output()

    return bert_encoder_layer


def load_data(config):
    df = pd.read_csv(config['data_dir'] + os.sep + "olid-training-v1.0.tsv", sep="\t", header=0)
    sents = df['tweet']
    label_a = df['subtask_a']
    label_b = df['subtask_b']
    return sents, label_a.tolist(), label_b.tolist()


def clean_tweets(tweets):
    text_processor = TextPreProcessor(
        # terms that will be normalized
        normalize=['email', 'phone',
                   'time', 'date', 'number'],
        # terms that will be annotated
        annotate={},
        fix_html=False,  # fix HTML tokens

        # corpus from which the word statistics are going to be used
        # for word segmentation
        segmenter="twitter",

        # corpus from which the word statistics are going to be used
        # for spell correction
        corrector="twitter",

        unpack_hashtags=True,  # perform word segmentation on hashtags
        unpack_contractions=False,  # Unpack contractions (can't -> can not)
        spell_correct_elong=False,  # spell correction for elongated words

    )
    tweets = [re.sub(r"(#\w+)", "#\g<1>#", t) for t in tweets.tolist()]
    for i in range(len(tweets)):
        # tweets[i] = re.sub(r"(#\w+)", "#\1#", tweets[i])
        tweets[i] = text_processor.pre_process_doc(tweets[i])
        tweets[i] = emoji.demojize(tweets[i])
    return tweets


config = {'bert_config': 'cased_L-12_H-768_A-12/bert_config.json',
          'data_dir': './dataset',
          'vocab_file': 'cased_L-12_H-768_A-12/bert_config.json',
          'do_train': True
          }
sents,label_a,label_b = load_data(config)

sents = clean_tweets(sents)
input_ids, input_mask, input_tokens = tokenize(sents, max_seq_len=64)

with tf.variable_scope('bert_embedding'):
    bert_config = modelling.BertConfig.from_json_file(config['vocab_file'])
    bert_encoder_layer = bert_transformer(input_ids, input_mask, bert_config, config)

print("Done bert.")
