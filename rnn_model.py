import tensorflow as tf
import numpy as np

class RNN_Model(object):



    def __init__(self,config,is_training=True):

        self.keep_prob=config.keep_prob
        self.batch_size=tf.Variable(0,dtype=tf.int32,trainable=False)

        num_step=config.num_step

        # dimension-0 is batch,dimension-1 is num_step
        self.input_data=tf.placeholder(tf.int32,[None,num_step])

        # dimension-0 is batch
        self.target = tf.placeholder(tf.int64,[None])

        # dimension-0 is num_step, dimension-1 is batch
        self.mask_x = tf.placeholder(tf.float32,[num_step,None])

        class_num=config.class_num
        hidden_neural_size=config.hidden_neural_size
        vocabulary_size=config.vocabulary_size
        embed_dim=config.embed_dim
        hidden_layer_num=config.hidden_layer_num
        self.batch_size = batch_size = config.batch_size

        #build LSTM network

        lstm_cell = tf.contrib.rnn.GRUCell(hidden_neural_size)
        if self.keep_prob<1:
            lstm_cell =  tf.contrib.rnn.DropoutWrapper(
                lstm_cell,output_keep_prob=self.keep_prob
            )

        cell = tf.contrib.rnn.MultiRNNCell([lstm_cell]*hidden_layer_num,state_is_tuple=True)

        self._initial_state = cell.zero_state(self.batch_size,dtype=tf.float32)

        #embedding layer
        with tf.device("/cpu:0"),tf.name_scope("embedding_layer"):
            embedding = tf.get_variable("embedding",[vocabulary_size,embed_dim],dtype=tf.float32)
            inputs=tf.nn.embedding_lookup(embedding,self.input_data)

        if self.keep_prob<1:
            inputs = tf.nn.dropout(inputs,self.keep_prob)

        # inputs: dimension-0 batch, dimension-1 time_step, dimension-2 embeddding layer, shared variables
        # inputs = [tf.squeeze(input_, [1])
        #   for input_ in tf.split(inputs, num_step, 1)]

        # unroll lstm
        state=self._initial_state
        with tf.variable_scope("LSTM_layer"):
            #tf.get_variable_scope().reuse_variables()
            out_put, state = tf.nn.dynamic_rnn(cell = cell, inputs = inputs,initial_state = state, scope = "LSTM_layer")
            # for time_step in range(num_step):
            #     if time_step>0: tf.get_variable_scope().reuse_variables()
            #     (cell_output,state)=cell(inputs[:,time_step,:],state)
            #     out_put.append(cell_output)
        out_put = tf.transpose(out_put,perm = [1,0,2])
        out_put=out_put*self.mask_x[:,:,None]

        with tf.name_scope("mean_pooling_layer"):
            # mask the matrix
            out_put=tf.reduce_sum(out_put,0)/(tf.reduce_sum(self.mask_x,0)[:,None])

        with tf.name_scope("Softmax_layer_and_output"):
            softmax_w = tf.get_variable("softmax_w",[hidden_neural_size,class_num],dtype=tf.float32)
            softmax_b = tf.get_variable("softmax_b",[class_num],dtype=tf.float32)
            self.logits = tf.matmul(out_put,softmax_w)+softmax_b

        with tf.name_scope("loss"):
            self.loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits= self.logits+1e-10,labels=self.target)
            self.cost = tf.reduce_mean(self.loss)

        with tf.name_scope("accuracy"):
            self.prediction = tf.argmax(self.logits,1)
            correct_prediction = tf.equal(self.prediction,self.target)
            self.correct_num=tf.reduce_sum(tf.cast(correct_prediction,tf.float32))
            self.accuracy = tf.reduce_mean(tf.cast(correct_prediction,tf.float32),name="accuracy")

        #add summary
        loss_summary = tf.summary.scalar("loss",self.cost)
        #add summary
        accuracy_summary=tf.summary.scalar("accuracy_summary",self.accuracy)

        if not is_training:
            return

        self.globle_step = tf.Variable(0,name="globle_step",trainable=False)
        self.lr = tf.Variable(0.0,trainable=False)

        tvars = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(tf.gradients(self.cost, tvars),
                                      config.max_grad_norm)


        # Keep track of gradient values and sparsity (optional)
        grad_summaries = []
        for g, v in zip(grads, tvars):
            if g is not None:
                grad_hist_summary = tf.summary.histogram("{}/grad/hist".format(v.name), g)
                sparsity_summary = tf.summary.scalar("{}/grad/sparsity".format(v.name), tf.nn.zero_fraction(g))
                grad_summaries.append(grad_hist_summary)
                grad_summaries.append(sparsity_summary)
        self.grad_summaries_merged = tf.summary.merge(grad_summaries)

        self.summary =tf.summary.merge([loss_summary,accuracy_summary,self.grad_summaries_merged])



        optimizer = tf.train.AdamOptimizer(self.lr)
        #optimizer.apply_gradients(zip(grads, tvars))
        self.train_op=optimizer.apply_gradients(zip(grads, tvars))

        # self.new_lr = tf.placeholder(tf.float32,shape=[],name="new_learning_rate")
        # self._lr_update = tf.assign(self.lr,self.new_lr)

    # def assign_new_lr(self,session,lr_value):
    #     session.run(self._lr_update,feed_dict={self.new_lr:lr_value})
    # def assign_new_batch_size(self,session,batch_size_value):
    #     session.run(self._batch_size_update,feed_dict={self.new_batch_size:batch_size_value})
