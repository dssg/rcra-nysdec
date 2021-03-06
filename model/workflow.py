from drain import step, model, util
from drain.util import dict_merge
from .transform import EpaTransform
from ..output.aggregations import spacedeltas
from itertools import product

YEARS = range(2010, 2016+1) + [2017]

ACTIVE = 'handler_received and (active_today or (handler_age < 365) or br)'
LQG = '(manifest_monthly_3y_approx_qty_max >= 2200)'
LQG_UNINSPECTED_3Y = '~(last_investigation_days < 1095) and (manifest_monthly_3y_approx_qty_max >= 2200)'
LQG_UNINSPECTED_5Y = '~(last_investigation_days < 1825) and (manifest_monthly_3y_approx_qty_max >= 2200)'
R2_LQG_UNINSPECTED = "~(last_investigation_days < 1825) and state_district == 'NYSDEC R2' and (manifest_monthly_3y_approx_qty_max >= 2200)"

QUERIES = [ACTIVE, LQG, LQG_UNINSPECTED_3Y]

aggregations = {a: {level: indexdelta[1]  for level, indexdelta in s.items()}
                for a,s in spacedeltas.iteritems()}

def aggregations_by_index(names):
    return {a: util.dict_subset(d, names) for a,d in aggregations.items()}

violation_state_args = dict(
    outcome_expr='aux.violation_state',
    train_query='evaluation_state and ' + LQG,
    evaluation=False,
    aggregations=aggregations_by_index(['facility'])
)

violation_epa_args = dict(
    outcome_expr='aux.violation_epa',
    train_query='evaluation_epa', 
    evaluation=False
)

violation_args = dict(
    outcome_expr='aux.violation',
    train_query='evaluation', 
    evaluation=False
)

evaluation_state_args = dict(
    outcome_expr='aux.evaluation_state', 
    train_query=LQG,
    evaluation=True,
    aggregations=aggregations_by_index(['facility'])
)

evaluation_and_violation_state_args = dict(
    outcome_expr='aux.evaluation_state & aux.violation_state', 
    train_query=LQG,
    evaluation=True,
    aggregations=aggregations_by_index(['facility'])
)


evaluation_state_lqg_args = util.dict_merge(evaluation_state_args,
    dict(train_query='aux.manifest_monthly_3y_approx_qty_max >= 1000'))

evaluation_args = dict(
    outcome_expr='aux.evaluation', 
    train_query=['aux.active_today | aux.evaluation | (aux.handler_age < 365) | aux.br',
            ], 
    evaluation=True
)

forest = {'_class_name':['sklearn.ensemble.RandomForestClassifier'], 
        'n_estimators':[10000],
        'criterion':['entropy'],
        'balanced':[True],
        'max_features':['sqrt'],
        'random_state':[0],
        'n_jobs':[-1]}

logit = {'_class_name':['sklearn.linear_model.LogisticRegression'],
        'penalty':['l1'], 'C':[0.01]}

adaboost = {'_class_name':['sklearn.ensemble.AdaBoostClassifier'],
            'n_estimators':[25],
            'learning_rate':[1]}

gradient = {'_class_name':['sklearn.ensemble.GradientBoostingClassifier'],
            'loss':['deviance'],
            'learning_rate':[0.01],
            'n_estimators':[100],
            'max_depth':[3],
            'random_state':[0]}

svm = {'_class_name':['sklearn.svm.LinearSVC'],
        'C':[.01], 'penalty':['l1'], 'dual':[False]}

forest_search = {'_class_name':['sklearn.ensemble.RandomForestClassifier'], 
        'n_estimators':[500],
        'criterion': ['entropy', 'gini'],
        'max_features':['sqrt','log2'],
        'n_jobs':[-1], 'random_state':[0]}

logit_search = {'_class_name':['sklearn.linear_model.LogisticRegression'],
        'penalty':['l1','l2'], 'C':[.01,.1,1,10]}

adaboost_search = {'_class_name':['sklearn.ensemble.AdaBoostClassifier'],
            'n_estimators':[25,50,100]}

svm_search = [{'_class_name':['sklearn.svm.LinearSVC'],
        'C':[.01,.1,1], 'penalty':['l2'], 'dual':[True,False]},
        {'_class_name':['sklearn.svm.LinearSVC'],
        'C':[.01,.1,1], 'penalty':['l1'], 'dual':[False]}]

gradient_search = {'_class_name':['sklearn.ensemble.GradientBoostingClassifier'],
            'loss':['deviance'],
            'learning_rate':[.01, 0.1, 1],
            'n_estimators':[50, 100, 200],
            'max_depth':[2,3,4]}


### the "baseline" models are random forests with manually selected train_years
def violation_state_baseline():
    return models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), 
                  estimator_search=forest) 

def violation_state_baseline_logit():
    transform_search = dict(train_years=5, year=YEARS, **violation_state_args)
    return models(transform_search=transform_search, estimator_search=logit) 

def violation_state_forest_states():
    return models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), 
                  estimator_search=util.dict_merge(forest, {'random_state':range(4)}))

def violation_state_forest_states_4k():
    return models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), 
            estimator_search=util.dict_merge(forest, {'n_estimators':4000, 'random_state':range(4)}))


def evaluation_state_baseline():
    return models(transform_search= dict(train_years=3, year=YEARS, **evaluation_state_args), estimator_search=forest)

def evaluation_state_baseline_logit():
    return models(transform_search= dict(train_years=5, year=YEARS, **evaluation_state_args), estimator_search=logit) 

def evaluation_state_baseline_logit_predict_train():
    return models(transform_search= dict(train_years=5, year=YEARS, **evaluation_state_args), estimator_search=logit, predict_train=True) 


def evaluation_and_violation_state():
    return models(transform_search= dict(train_years=3, year=YEARS, **evaluation_and_violation_state_args), estimator_search=forest)

def evaluation_and_violation_state_product():
    return evaluation_and_violation_models(evaluation_state_baseline(), violation_state_baseline())

def evaluation_and_violation_state_product_logit():
    return evaluation_and_violation_models(evaluation_state_baseline_logit(), violation_state_baseline_logit())


def violation_state_big_loop():
    transform_search = dict(
            evaluation=False,
            year=YEARS,
            train_years=[5,8],
            aggregations=aggregations,
    )
    s = []
    outcome_expr = ['aux.violation', 'aux.violation_state']
    train_query = ['evaluation', 'evaluation_state']

    for o, t in zip(outcome_expr, train_query):
        transform_search.update(outcome_expr=o)
        transform_search.update(train_query=
                [t] + [t + ' and ' + q for q in QUERIES])
        s += models(transform_search=transform_search, 
                    estimator_search=forest)
        s += models(transform_search=transform_search, 
                    estimator_search=logit)
    return s

def violation_state_ipw_big_loop():
    transform_search = dict(
            year=YEARS,
            aggregations=aggregations
    )
    s = []

    for y, q, e in product([5,8], QUERIES, [logit,forest]):
        tsi = dict(train_years=y, **transform_search)
        tsv = dict(train_years=y, **transform_search)
        
        tsi.update(train_query=q,
                   evaluation=True,
                   outcome_expr='aux.evaluation_state')

        i = models(transform_search=tsi,
                   estimator_search=logit,
                   predict_train=True)

        tsv.update(train_query='evaluation_state and ' + q,
                   evaluation=False,
                   outcome_expr='aux.violation_state')

        s += models(transform_search=tsv, 
                    estimator_search=e, 
                evaluation_models=i)
    return s


def violation_state_ipw():
    transform_search=dict(train_years=5, year=YEARS, **violation_state_args)
    return models(transform_search=transform_search, 
                  estimator_search=forest, 
                  evaluation_models = evaluation_state_baseline_logit_predict_train()) 

def violation_state_ipw_states():
    transform_search=dict(train_years=5, year=YEARS, **violation_state_args)
    return models(transform_search=transform_search, 
            estimator_search=dict_merge(forest, dict(random_state=range(4))), 
                  evaluation_models = evaluation_state_baseline_logit_predict_train()) 


def violation_state_ipw_logit():
    transform_search=dict(train_years=5, year=YEARS, **violation_state_args)
    return models(transform_search=transform_search, 
                  estimator_search=logit, 
                  evaluation_models = evaluation_state_baseline_logit_predict_train()) 


# for dumping data for storing
def violation_state_data():
    data = [m.inputs[1] for m in models(transform_search= dict(train_years=5, year=range(2012,2017), **violation_state_args), estimator_search=forest)]
    for d in data:
        d.target = True

    return data

def violation_state_datasets():
    transform_search = dict(train_years=5, year=YEARS, **violation_state_args)
    #transform_search['aggregations'] = [util.dict_subset(aggregations_by_index(['facility']), set(aggregations.keys()).difference([name])) for name in aggregations.keys()]
    transform_search['aggregations'] = [util.dict_subset(aggregations_by_index(['facility']), [name]) for name in aggregations.keys()]
                                        
    return models(transform_search=transform_search, estimator_search=forest)


def violation_state_aggregation_levels():
    transform_search = dict(train_years=5, year=YEARS, **violation_state_args)
    transform_search['aggregations'] = [
            aggregations_by_index(names) for names in [[], ['facility'], ['facility', 'zip'], ['facility', 'entity'], ['facility', 'zip', 'entity']]
    ]
                                        
    return models(transform_search=transform_search, estimator_search=forest)

# vary train years
def violation_state_train_years():
    return models(transform_search= dict(train_years=range(1,10+1), year=YEARS, **violation_state_args), estimator_search=forest) +\
            models(transform_search= dict(train_years=range(1,10+1), year=YEARS, **violation_state_args), estimator_search=logit)

def violation_state_train_queries():
    transform_search = util.dict_merge(violation_state_args, 
            dict(year=YEARS, train_years=5, 
                 train_query=["evaluation_state"] + ["evaluation_state and " + q for q in QUERIES] ))

    return models(transform_search= transform_search, estimator_search=forest)

def evaluation_state_aggregation_levels():
    transform_search = dict(train_years=5, year=YEARS, **evaluation_state_args)
    transform_search['aggregations'] = [
            aggregations_by_index(names) for names in [[], ['facility'], ['facility', 'zip'], ['facility', 'entity'], ['facility', 'zip', 'entity']]
    ]
                                        
    return models(transform_search=transform_search, estimator_search=logit)

# vary train years
def evaluation_state_train_years():
    return models(transform_search=dict(train_years=range(1,8), year=YEARS, **evaluation_state_args), 
                  estimator_search=logit)

def evaluation_state_train_queries():
    transform_search = util.dict_merge(evaluation_state_args, 
            dict(year=YEARS, train_years=5, 
                 train_query=QUERIES ))

    return models(transform_search= transform_search, estimator_search=logit)


# grid searches for various model classes
def violation_state_adaboost():
    return models(transform_search=dict(train_years=[5], year=YEARS, **violation_state_args), estimator_search=adaboost_search)

def violation_state_gradient():
    return models(transform_search=dict(train_years=[5], year=YEARS, **violation_state_args), estimator_search=gradient_search)


def violation_state_forest():
    return models(transform_search=dict(train_years=[5], year=YEARS, **violation_state_args),
                  estimator_search=forest_search)

def violation_state_logit():
    transform_search=dict(train_years=[5], year=YEARS, **violation_state_args)
    transform_search['aggregations'] = [aggregations_by_index(names) for names in  [
        [], 
        ['facility'], 
        ['facility', 'zip'], 
        ['facility', 'entity'], 
        ['facility', 'zip', 'entity']
    ]]
     
    return models(transform_search=transform_search, estimator_search=logit_search)

def violation_state_svm():
    transform_search=dict(train_years=[5], year=YEARS, **violation_state_args)
    transform_search['aggregations'] = [aggregations_by_index(names) for names in  [
        [], 
        ['facility'], 
        #['facility', 'zip'], 
        #['facility', 'entity'], 
        #['facility', 'zip', 'entity']
    ]]
 
    return models(transform_search=transform_search, estimator_search=svm_search[0]) +\
           models(transform_search=transform_search, estimator_search=svm_search[1])

# the best model of each class
def violation_state_best():
    return (models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), estimator_search=logit) +
            models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), estimator_search=forest) +
            models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), estimator_search=svm) +
            models(transform_search= dict(train_years=5, year=YEARS, **violation_state_args), estimator_search=gradient))

## national models

def violation_fast():
    return models(transform_search= dict(train_years=1, year=2016, **violation_args), estimator_search=forest)

def violation():
    return models(transform_search= dict(train_years=2, **violation_args), estimator_search=forest)

region_4_violation_types = [
        '262.A',
        # 264.*
        '264.A', '264.AA', '264.B', '264.BB', '264.C', '264.CC', '264.D', '264.DD', '264.E', 
        '264.EE', '264.F', '264.G', '264.H', '264.I', '264.J', '264.K', '264.L', '264.M', 
        '264.N', '264.O', '264.S', '264.W', '264.X', 
        # 268.*
        '268.A', '268.B', '268.C', '268.D', '268.E', 
        # 270.*
        '270.A', '270.B', '270.C', '270.D', '270.F', '270.G', '270.H', '270.I', 
        '265.J', '265.BB', '265.CC'
]

# use where() so that it's null when not evaluated by epa
region_4_outcome_expr = "aux.violation_types_epa.apply(lambda v, vt=set([%s]): not vt.isdisjoint(v)).where(aux.evaluation_epa)" % \
        str.join(',', ["'%s'" % v for v in region_4_violation_types])

region_4_args = dict(
    outcome_expr=region_4_outcome_expr,
    train_query='aux.evaluation_epa',
    region=4,
    evaluation=False)

def violation_region_4():
    return models(transform_search= dict(train_years=5, **region_4_args), estimator_search=forest)


def violation_best():
    return models(transform_search= dict(train_years=2, **violation_args), estimator_search=forest) + \
            models(transform_search=violation_args, estimator_search=logit)
            #models(transform_search= violation_args, estimator_search=svm)

def violation_train_years():
    return models(transform_search=dict(train_years=range(1,6), **violation_args),
            estimator_search=forest)

def violation_region():
    return models(transform_search=dict(region=range(1,11),train_years=5, **violation_args), 
            estimator_search=forest)

def violation_logit():
    return models(transform_search=violation_args, estimator_search = logit_search)

def violation_forest():
    return models(transform_search=violation_args, estimator_search = forest_search)

def violation_svm():
    return models(transform_search=violation_args, estimator_search = svm_search[0]) + \
           models(transform_search=violation_args, estimator_search = svm_search[1])

def violation_all():
    return violation_logit() + violation_forest() + violation_svm() + violation_train_years() + violation_region()

def evaluation():
    return models(transform_search=dict(train_years=4, **evaluation_args), estimator_search=forest)

def calibrated_evaluation():
    return calibrated_models(transform_search={'outcome':['evaluation_epa'], 'train_years':[4], 'year':[2012],
    }, estimator_search = forest)

def evaluation_and_violation():
    return evaluation_and_violation_models(evaluation(), violation_best())

def evaluation_and_violation_region_4():
    return evaluation_and_violation_models(evaluation(), violation_region_4())

def evaluation_best():
    return models(transform_search=evaluation_args, estimator_search=forest) + \
            models(transform_search=evaluation_args, estimator_search=svm) + \
            models(transform_search=evaluation_args, estimator_search=logit)


# Utilities for generated various workflows
def evaluation_and_violation_models(es, vs):
    evs = []
    for e in es:
        e_year = e.inputs[1].year
        e.get_input('transform').name = 'e_transform'
        e.get_input('estimator').name = 'e_estimator'
        e.get_input('y').name = 'e_y'
        for v in vs:
            v_year = v.inputs[1].year
            if e_year == v_year:
                ev = model.PredictProduct(inputs= [e,v], 
                    inputs_mapping=['evaluation', 'violation'])
                ev.target = True
                evs.append(ev)
    return evs

def calibrated_violation():
    return calibrated_models(transform_search= {'outcome':['violation_epa'], 'year':[2012], 'train_years': [2],
            }, estimator_search=forest)

def calibrated_evaluation_and_violation():
    e = calibrated_evaluation()[0]
    v = calibrated_violation()[0]
    ve = model.PredictProduct(inputs= [e,v], inputs_mapping=['inspection', 'violation'])
    ve.target = True

    ve.get_input('transform').name = 'transform2'
    ve.get_input('estimator').name = 'estimator2'
    ve.get_input('y').name = 'y2'
    return [ve]


def models(transform_search, estimator_search, evaluation_models=None, predict_train=False):
    """
    Args:
        transform_search: args to search over for EpaTransform
        estimator_search: args to search over for Construct of estimator
        evaluation_models: optional list of models to use for inverse probability weighting
        test: whether or not to predict on training set
    """
    steps = []

    if evaluation_models is not None:
        for e in evaluation_models:
            t = e.get_input('transform')
            m = e.get_input('estimator')
            y = e.get_input('y')
            if t is not None: t.name = 'ipw_transform'
            if m is not None: m.name = 'ipw_estimator'
            if y is not None: y.name = 'ipw_y'

    for transform_args, estimator_args in product(
            util.dict_product(transform_search), 
            util.dict_product(estimator_search)):

        transform = EpaTransform(month=2, day=1, **transform_args)
        transform.name='transform'

        estimator = step.Construct(**estimator_args)
        estimator.name='estimator'

        if evaluation_models is None:
            y = model.FitPredict(inputs=[estimator, transform], predict_train=predict_train)
            y.target = True
            y.name = 'y'

            steps.append(y)
        else:
            # find all evaluation models of the same year and add them via IPW
            for e in evaluation_models:
                if e.inputs[1].year == transform.year:
                    ipw = model.InverseProbabilityWeights(inputs=[e, transform])
                    y = model.FitPredict(inputs=[estimator, transform, ipw])
                    y.target = True
                    y.name = 'y'
                    steps.append(y)

    return steps


def calibrated_models(transform_search={}, estimator_search={}):
    steps = []
    transform_search = util.dict_merge(dict(
        train_years = [3],
        year=range(2012,2015+1)
    ), transform_search)

    for transform_args, estimator_args in product(
            util.dict_product(transform_search), 
            util.dict_product(estimator_search)):

        transform = EpaTransform(month=1, day=1, **transform_args)
        transform.name = 'transform'
        
        estimator = step.Construct(**estimator_args)
        estimator.name = 'estimator'
        calibrator =  step.Construct('sklearn.calibration.CalibratedClassifierCV', cv=10,
                inputs=[estimator], inputs_mapping=['base_estimator'])
        calibrator.name = 'calibrator'

        y = model.FitPredict(inputs=[calibrator, transform])
        y.target = True
        y.name = 'y'
        steps.append(y)

    return steps
