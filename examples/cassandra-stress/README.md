# Main configuration files

See ansible/templates/stress.yaml for the configuration for `cassandra-stress`; the column family, distribution of data
and

# Start and configure the cluster

```
cp cluster1.yaml mycluster.yaml

ops mycluster.yaml terraform plan
ops mycluster.yaml terraform apply
ops mycluster.yaml play ansible/setup.yaml

```


# Run stress tests

```
# ssh on the bastion where the stress configurations are located
ops mycluster.yaml ssh bastion

# insert one million rows
cassandra-stress user profile=/etc/cassandra/conf/stress.yaml ops\(insert=1\) n=1000000 -node cassandra-1

# mixed workload with 9 selects and 1 inserts
cassandra-stress user profile=/etc/cassandra/conf/stress.yaml ops\(insert=1,dgraph=9\) n=1000000 -node cassandra-1

# specifying number of threads
cassandra-stress user profile=/etc/cassandra/conf/stress.yaml ops\(insert=1,dgraph=9\) n=1000000 -rate threads=50 -node cassandra-1
```

# Example results

```

type,      total ops,    op/s,    pk/s,   row/s,    mean,     med,     .95,     .99,    .999,     max,   time,   stderr, errors,  gc: #,  max ms,  sum ms,  sdv ms,      mb
total,       1000000,   32277,   32277,   32277,     3.1,     2.0,     8.0,    26.2,    33.9,    61.4,   32.5,  0.03181,      0,      0,       0,       0,       0,       0


Results:
op rate                   : 30750 [dgraph:30750]
partition rate            : 30750 [dgraph:30750]
row rate                  : 30750 [dgraph:30750]
latency mean              : 3.2 [dgraph:3.2]
latency median            : 2.0 [dgraph:2.0]
latency 95th percentile   : 7.3 [dgraph:7.3]
latency 99th percentile   : 19.3 [dgraph:19.3]
latency 99.9th percentile : 88.7 [dgraph:88.7]
latency max               : 648.3 [dgraph:648.3]
Total partitions          : 1000000 [dgraph:1000000]
Total errors              : 0 [dgraph:0]
total gc count            : 0
total gc mb               : 0
total gc time (s)         : 0
avg gc time(ms)           : NaN
stdev gc time(ms)         : 0
```

# Testing cassandra 1.2

Because it doesn't support cql V2, we have to use the legacy mode for cassandra test

```
cassandra-stress write n=1000000 -col n=fixed\(3\) \
size=fixed\(34\) -rate threads=100 -log interval=10 \
-mode thrift -node cassandra-1
```



