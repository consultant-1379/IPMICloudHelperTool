#!/bin/bash

CAT=/bin/cat
CURL=/usr/bin/curl
ECHO=/bin/echo
GREP=/bin/grep
LOGGER=/bin/logger
PING=/bin/ping
RM=/bin/rm
SED=/bin/sed


ATVPCSPP12=( "atvpcspp12.athtem.eei.ericsson.se" "10.82.23.20" )
CIFWK=( "cifwk-oss.lmera.ericsson.se" "10.42.34.189" )

API_GETGATEWAY="/Vms/gateway_hostname"
API_GETSPP="/getSpp/?gateway"
POD_DEFAULT="https://atvcloud3.athtem.eei.ericsson.se/"
TAG="ipmitool.cloud.postinstall"
POD_PREFIX_URL="pod_prefix_url"
IPMI_CONF=/opt/ericsson/nms/litp/etc/ipmitool.conf



log()
{
    ${LOGGER} -t ${TAG} "$*"
}

_CURL()
{
    local _sources_=( $1 )
    local _api_="$2"
    local _ok_=1
    for _source_ in ${_sources_[*]} ; do
        local _cmd_="${CURL} --insecure -s https://${_source_}${_api_}"
        log "Running: ${_cmd_}"
        _res_=`${_cmd_} 2>&1`
        local _rc_=$?
        log "Got back: ${_res_}"
        if [ ${_rc_} -eq 0 ] ; then
            ${ECHO} "${_res_}"
            _ok_=0
            break
        fi
    done
    return ${_ok_}
}

#
# Get the SPP POD for a gateway VM and set it for later
# use by ipmitool.cloud
#
main()
{
    ${CAT} /etc/resolv.conf | ${GREP} "192.168.0.1" > /dev/null 2>&1
    if [ $? -ne 0 ] ; then
        ${ECHO} "nameserver 192.168.0.1" >> /etc/resolv.conf
        log "Added 192.168.0.1 as a nameserver"
    fi

    local _gatewayhn_
    _gatewayhn_=`_CURL "${ATVPCSPP12[*]}" ${API_GETGATEWAY}`
    if [ $? -ne 0 ] ; then
        log "Could not find gateway address from any of: ${ATVPCSPP12[*]}!"
        exit 1
    fi
    log "Gateway is ${_gatewayhn_}"
    
    local _pod_
    _pod_=`_CURL "${CIFWK[*]}" ${API_GETSPP}=${_gatewayhn_}`
    if [ $? -ne 0 ] ; then
        log "Could not find POD address from any of: ${CIFWK[*]}!"
        exit 1
    fi
    ${ECHO} "${_pod_}" | ${GREP} "does not exist" > /dev/null 2>&1
    if [ $? -eq 0 ] ; then
        log "${_pod_}, using default ${POD_DEFAULT}"
        _pod_=${POD_DEFAULT}
    fi
    log "POD is ${_pod_}"
    if [ ! -f ${IPMI_CONF} ] ; then
        ${ECHO} "${POD_PREFIX_URL}=${_pod_}" > ${IPMI_CONF}
    else
        ${SED} -i "s|^${POD_PREFIX_URL}=.*|${POD_PREFIX_URL}=${_pod_}|" ${IPMI_CONF}
    fi
    log "Set ${POD_PREFIX_URL} for ${_gatewayhn_} to ${_pod_}"
}

main
exit 0
